from requests import Session, ConnectionError
from itertools import count
from typing import NamedTuple, Callable, Awaitable
import asyncio
from types import SimpleNamespace
import time

URL_BASE = "http://wra3-el.local:4030/"
s = Session()


# non-blocking functions

def request(fn, *args, **kwargs):
    while True:
        try:
            res = fn(*args, **kwargs)
        except ConnectionError:
            print(f"Connection issue. Retrying IMMEDIATELY")
        else:
            break
    assert res.ok, res.text
    return res

def get(*args, **kwargs):
    return request(s.get, *args, **kwargs).json()

def post(*args, **kwargs):
    request(s.post, *args, **kwargs)

def delete(*args, **kwargs):
    request(s.delete, *args, **kwargs)

def getState():
    return get(URL_BASE + "state")

def readSensor(sensors, sensor_name):
    for sensor in sensors:
        if sensor["name"] == sensor_name:
            assert sensor["value"] == 'low' or sensor["value"] == 'high', sensor["value"]
            return sensor["value"] == 'high'
    raise Exception

def readCascadeSensor(sensor_name):
    return readSensor(getState()["data"]["liberty"]["data"]["sensors"], sensor_name)

def readVanguardSensor(mp, sensor_name):
    return readSensor(getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]["data"]["sensors"], sensor_name)

def _read_home_switch():
    return readCascadeSensor("filamentHome")

def _read_printhead_switch():
    return readCascadeSensor("printHead")

def _get_connected_mp_numbers():
    pods = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"]
    return tuple(i for i, pod in enumerate(pods) if pod is not None)

def getPrintheadEncoderCount() -> float:
    return get(URL_BASE + "firmwareCom/printhead/encoderDistance")

_read_printhead_encoder = getPrintheadEncoderCount

def deletePrintheadEncoderCount() -> None:
    delete(URL_BASE + "firmwareCom/printhead/encoderDistance")

_clear_printhead_encoder = deletePrintheadEncoderCount

def _read_temperatures():
    temperatures = getState()["data"]["apollo"]["context"]["temperatures"]["nozzle"]
    return SimpleNamespace(
        target=temperatures["target"],
        actual=temperatures["actual"]
    )


# blocking functions

class LibertyJob(NamedTuple):
    print_text: str
    path: str
    default_json: dict
    job_name: str

async def waitLibertyJobDoneAsync(job_name: str, ignore_timestamp):
    while True:
        job = getState()["data"]["liberty"]["job"]
        if job is not None and job["time"]["started"] != ignore_timestamp and job["name"] == job_name and job["finished"]:
            return
        await asyncio.sleep(0.2)

def libertyDoJob(job: LibertyJob, json):
    j = job.default_json.copy()
    j.update(json)
    print(job.print_text, j)
    old_job = getState()["data"]["liberty"]["job"]
    ignore_timestamp = old_job["time"]["started"] if old_job is not None else None
    post(URL_BASE + job.path, json=j)
    return waitLibertyJobDoneAsync(job.job_name, ignore_timestamp)

def wrapLibertyDoJob(job: LibertyJob):
    return lambda **json: libertyDoJob(job, json)

async def extrudeAsync(mm, rate=300):
    j = {"commands": ["M83", f"G1 F{rate} E{mm}"]}
    print("extrude", j)
    post(URL_BASE + "streamFromCommands", json=j)
    await asyncio.sleep(mm / rate * 60 * 1.01 + 0.5)

async def vanguardFeedAsync(mp, dist):
    j = {"id": mp, "distance": dist}
    print("feed", j)
    mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
    assert mp_obj is not None
    old_job = mp_obj["job"]
    ignore_timestamp = old_job["time"]["started"] if old_job is not None else None
    post(URL_BASE + "vanguard/feed", json=j)
    while True:
        mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
        assert mp_obj is not None
        job = mp_obj["job"]
        assert job is not None and job["name"] == "feeding", job
        if job["time"]["started"] != ignore_timestamp and job["finished"]:
            break
        await asyncio.sleep(0.2)

liberty_to_home = wrapLibertyDoJob(LibertyJob("to PX", "liberty/to-home", {"length": 0}, "toHome"))
liberty_to_printhead = wrapLibertyDoJob(LibertyJob("to printhead", "liberty/to-printhead", {"length": 0}, "toPrinthead"))
liberty_to_nozzle = wrapLibertyDoJob(LibertyJob("to nozzle", "liberty/to-nozzle", {"length": 0}, "toNozzle"))
liberty_unload = wrapLibertyDoJob(LibertyJob("unload", "liberty/unload", {"length": 0, "performCut": False, "useOutgoingSwitch": True}, "unloading"))
liberty_cut = wrapLibertyDoJob(LibertyJob("cut", "liberty/cut", {}, "cutting"))

VANGUARD_TASK_KIND = 0b001
LIBERTY_TASK_KIND =  0b010
EXTRUDE_TASK_KIND =  0b100

class PreparedTimeConsumingTask:
    def __init__(self, kinds, create_coro):
        self._kinds = kinds
        self._create_coro = create_coro
    def start_and_wait_til_done(self):
        asyncio.run(self._create_coro())

def _to_home(mp):
    return PreparedTimeConsumingTask(LIBERTY_TASK_KIND | VANGUARD_TASK_KIND, (lambda: liberty_to_home(materialPod=mp)))

def _mp_feed_filament_forward(mp, dist):
    return PreparedTimeConsumingTask(VANGUARD_TASK_KIND, (lambda: vanguardFeedAsync(mp, dist)))

def _cut():
    return PreparedTimeConsumingTask(LIBERTY_TASK_KIND, liberty_cut)

def _to_printhead(mp):
    return PreparedTimeConsumingTask(LIBERTY_TASK_KIND | VANGUARD_TASK_KIND, (lambda: liberty_to_printhead(materialPod=mp)))

def _to_nozzle_old(mp):
    return PreparedTimeConsumingTask(LIBERTY_TASK_KIND | VANGUARD_TASK_KIND, (lambda: liberty_to_nozzle(materialPod=mp)))

async def toNozzleSafeLoadImplementation(mp):
    print("-- special safe nozzle load beginning --")
    await vanguardFeedAsync(mp, 34)
    while True:
        deletePrintheadEncoderCount()
        await extrudeAsync(6)
        if getPrintheadEncoderCount() >= 3:
            break
        await vanguardFeedAsync(mp, 4)
    print("-- special safe nozzle load finished --")

def _to_nozzle_safe_load(mp):
    return PreparedTimeConsumingTask(VANGUARD_TASK_KIND | EXTRUDE_TASK_KIND, (lambda: toNozzleSafeLoadImplementation(mp)))

def _extrude(dist, rate):
    return PreparedTimeConsumingTask(EXTRUDE_TASK_KIND, (lambda: extrudeAsync(dist, rate)))

async def extrudeUntilPrintheadSwitchIsReleasedAndThenExtrudeOneMoreTimeImplementation(rate):
    while readCascadeSensor("printHead"):
        await extrudeAsync(100, rate)
    await extrudeAsync(100, rate)

def _extrude_until_printhead_switch_is_released_and_then_extrude_one_more_time(rate):
    return PreparedTimeConsumingTask(EXTRUDE_TASK_KIND, (lambda: extrudeUntilPrintheadSwitchIsReleasedAndThenExtrudeOneMoreTimeImplementation(rate)))

def _unload(mp):
    return PreparedTimeConsumingTask(LIBERTY_TASK_KIND | VANGUARD_TASK_KIND, (lambda: liberty_unload(materialPod=mp)))

def run_multiple_time_consuming_tasks_in_parallel(*tasks: PreparedTimeConsumingTask):
    has_vanguard_task = False
    has_liberty_task = False
    has_extrude_task = False
    for task in tasks:
        if task._kinds & VANGUARD_TASK_KIND:
            assert not has_vanguard_task, "cannot do multiple material pod jobs at the same time"
            has_vanguard_task = True
        if task._kinds & LIBERTY_TASK_KIND:
            assert not has_liberty_task, "cannot do multiple Element jobs at the same time"
            has_liberty_task = True
        if task._kinds & EXTRUDE_TASK_KIND:
            assert not has_extrude_task, "cannot do multiple extruder jobs at the same time"
            has_extrude_task = True
    async def run_tasks():
        await asyncio.gather(*(task._create_coro() for task in tasks))
    asyncio.run(run_tasks()) 

instantaneous_task = SimpleNamespace(
    read_temperatures=_read_temperatures, # takes no args, returns object with properties ".target" and ".actual"
    get_connected_mp_numbers=_get_connected_mp_numbers, # takes no args, returns a tuple of ints
    read_home_switch=_read_home_switch, # takes no args, returns True or False. (True means pressed)
    read_printhead_switch=_read_printhead_switch, # takes no args, returns True or False. (True means pressed)
    clear_printhead_encoder=_clear_printhead_encoder, # takes no args, returns nothing
    read_printhead_encoder=_read_printhead_encoder, # takes no args, returns a float
)

time_consuming_task = SimpleNamespace(
    # currently none of these return anything after comleting
    to_home=_to_home, # takes mp number
    mp_feed_filament_forward=_mp_feed_filament_forward, # takes mp number and mm distance
    cut=_cut, # takes no args
    to_printhead=_to_printhead, # takes mp number
    to_nozzle_old=_to_nozzle_old, # takes mp number
    to_nozzle_safe_load=_to_nozzle_safe_load, # takes mp number
    extrude=_extrude, # takes a mm distance and the feed rate
    extrude_until_printhead_switch_is_released_and_then_extrude_one_more_time=_extrude_until_printhead_switch_is_released_and_then_extrude_one_more_time, # takes feed rate
    unload=_unload, # takes mp number
)


##########################################################
##########################################################
### USER CODE BELOW

def main():
    temps = instantaneous_task.read_temperatures()
    assert temps.target >= 200 and temps.actual >= 200, f"Nozzle temperature is not high enough. Has target: {temps.target} and actual: {temps.actual}"

    mps = instantaneous_task.get_connected_mp_numbers()
    assert len(mps) > 0, "no MPs connected"
    print("MPs connected:", mps)
    if input("proceed? (y/n) ").strip().lower() != "y":
        return

    for i in count(0):

        print("cycles done:", i)

        for mp in mps:

            # make sure all the MPs we started with are still connected
            assert mps == instantaneous_task.get_connected_mp_numbers()

            time_consuming_task.to_home(mp).start_and_wait_til_done()
            # make sure we actually made it to home
            assert instantaneous_task.read_home_switch() == True

            time_consuming_task.to_printhead(mp).start_and_wait_til_done()
            # make sure we actually made it to printhead
            assert instantaneous_task.read_printhead_switch() == True

            # try to get filament up against the extruder gear.
            # If motor skips because it goes too far, that's fine
            time_consuming_task.mp_feed_filament_forward(mp, 51).start_and_wait_til_done() # 50mm? Idk
            
            while True:
                instantaneous_task.clear_printhead_encoder()
                run_multiple_time_consuming_tasks_in_parallel(
                    # IMPORTANT: notice how these ones don't have ".start_and_wait_til_done()"
                    time_consuming_task.extrude(30, 410), # distance 10mm, rate 600
                    time_consuming_task.mp_feed_filament_forward(mp, 25),
                    # you can run more than 2 in parallel. as many as you want
                    # ...
                )
                odometer_value = instantaneous_task.read_printhead_encoder()
                if odometer_value >= 20:
                    break
            time_consuming_task.cut().start_and_wait_til_done()

            run_multiple_time_consuming_tasks_in_parallel(
                time_consuming_task.extrude_until_printhead_switch_is_released_and_then_extrude_one_more_time(100), # rate 300
                time_consuming_task.unload(mp)
            )


if __name__ == "__main__":
    main()
