from requests import Session, ConnectionError
import time
from itertools import count
from typing import NamedTuple

URL_BASE = "http://5sd7-el.local:4030/"
s = Session()

def request(fn, *args, **kwargs):
    while True:
        try:
            res = fn(*args, **kwargs)
        except ConnectionError:
            RETRY_DELAY = 30
            print(f"Connection issue. Retrying in {RETRY_DELAY} seconds.")
            time.sleep(RETRY_DELAY)
        else:
            break
    assert res.ok, res.text
    return res

def get(*args, **kwargs):
    return request(s.get, *args, **kwargs).json()

def post(*args, **kwargs):
    request(s.post, *args, **kwargs)

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

def waitJobDone(job_name: str, ignore_timestamp) -> None:
    while True:
        job = getState()["data"]["liberty"]["job"]
        if job is not None and job["time"]["started"] != ignore_timestamp and job["name"] == job_name and job["finished"]:
            return
        time.sleep(0.2)

class Job(NamedTuple):
    print_text: str
    path: str
    default_json: dict
    job_name: str

def doJob(job: Job, json) -> None:
    j = job.default_json.copy()
    j.update(json)
    print(job.print_text, j)
    old_job = getState()["data"]["liberty"]["job"]
    ignore_timestamp = old_job["time"]["started"] if old_job is not None else None
    post(URL_BASE + job.path, json=j)
    waitJobDone(job.job_name, ignore_timestamp)

def wrapDoJob(job: Job):
    return lambda **json: doJob(job, json)

def getMpNumbers():
    pods = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"]
    ret = tuple(i for i, pod in enumerate(pods) if pod is not None)
    return ret

def extrude(mm):
    RATE = 300
    j = {"commands": ["M83", f"G1 F{RATE} E{mm}"]}
    print("extrude", j)
    post(URL_BASE + "streamFromCommands", json=j)
    time.sleep(mm / RATE * 60 * 1.1 + 1)

def vanguardFeed(mp, dist):
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
        time.sleep(0.2)

to_home = wrapDoJob(Job("to PX", "liberty/to-home", {"length": 0}, "toHome"))
to_printhead = wrapDoJob(Job("to printhead", "liberty/to-printhead", {"length": 0}, "toPrinthead"))
to_nozzle = wrapDoJob(Job("to nozzle", "liberty/to-nozzle", {"length": 0}, "toNozzle"))
unload = wrapDoJob(Job("unload", "liberty/unload", {"length": 0, "performCut": False, "useOutgoingSwitch": True}, "unloading"))
cut = wrapDoJob(Job("cut", "liberty/cut", {}, "cutting"))

def main():
    temperatures = getState()["data"]["apollo"]["context"]["temperatures"]["nozzle"]
    assert temperatures["target"] >= 0 and temperatures["actual"] >= 0, temperatures

    mps = getMpNumbers()
    assert len(mps) > 0, "no MPs connected"
    print("MPs connected:", mps)
    if input("proceed? (y/n) ").strip().lower() != "y":
        return

    # for mp in mps:
    #     print(mp, readVanguardSensor(mp, "outgoing"))
    #     if readVanguardSensor(mp, "outgoing"):
    #         assert mps == getMpNumbers()
    #         unload(materialPod=mp)

    for i in count(0):

        print("cycles done:", i)

        for mp in mps:
            assert mps == getMpNumbers()

            mpd = {"materialPod": mp}
            to_home(**mpd)
            assert readCascadeSensor("filamentHome")
            to_printhead(**mpd)
            assert readCascadeSensor("printHead")
            unload(**mpd)

if __name__ == "__main__":
    main()
