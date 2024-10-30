from itertools import count
from typing import NamedTuple, Callable, Awaitable
import asyncio
from types import SimpleNamespace
import time
from requests import Session, ConnectionError
import logging
from datetime import datetime

#Uncomment correct SOM
#SOM_NAME = "mosaic-mp-aqua-rig-1" #Rig 1
#SOM_NAME = "changeme-f8dc7a9fa4a0" #Rig 2
SOM_NAME = "changeme-f8dc7ab00fce" #Rig 3
#SOM_NAME = "" #Rig 4

URL_BASE = "http://"+ str(SOM_NAME) + ".local:4030/"

DATE = datetime.now()
FILE_NAME="testlog_" + str(DATE.strftime("%d_%m_%Y_%H_%M")) +  "_" + str(SOM_NAME)+".log"

logging.basicConfig(filename=FILE_NAME, 
					format='%(asctime)s %(message)s', 
					filemode='w') 
logger=logging.getLogger() 
logger.setLevel(logging.WARNING) 

s = Session()

#class object

class errorType:
    errorStatus = False
    errorDescription = "No Error"


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

'''def post(*args, **kwargs):
    request(s.post, *args, **kwargs)
'''
def post(url, *args, **kwargs):
    request(s.post, url, *args, **kwargs)

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

def getFeedEncoderCount(motor,mp) -> float:
    return get(URL_BASE + "vanguard/encoder-mm/" + str(motor) + "/" +str(mp) )

_read_feed_encoder = getFeedEncoderCount

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

async def unloadMP(mp,dist, cutStatus):
    j = {"performCut": cutStatus, "materialPod": mp, "useOutgoingSwitch": True, "checkLoaded": False}
    
    logText("Unload")
    start = time.time()
    errorMP = False
    try:
        post(URL_BASE + "liberty/unload", json=j)
    except:
        print("Exception in unload not of concern")
        #errorMP = True
    while not errorMP:
        mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
        if mp_obj is not None:
            job = mp_obj["job"]
            errorMP = checkForMPDisconnect(mp)
        else:
            logText("Disconnect during feed, end test")
            errorMP = True
        #errorMP = checkForMPDisconnect(mp)
        #print("Time" + str(time.time()- start))
        if time.time()- start > (dist/20 + 2):
            break
        await asyncio.sleep(2)

async def vanguardFeedAsync(mp, dist):
    j = {"distance": dist}
    logText("Feed"+ str( j))
    start = time.time()
    mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
    assert mp_obj is not None
    old_job = mp_obj["job"]
    ignore_timestamp = old_job["time"]["started"] if old_job is not None else None
    errorMP = False
    try:
        post(URL_BASE + "vanguard/feed/" + str(mp), json=j)
    except:
        print("Exception in feed, not of concern")
        #errorMP = True
    while not errorMP:
        mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
        if mp_obj is not None:
            job = mp_obj["job"]
            errorMP = checkForMPDisconnect(mp)
        else:
            logText("Disconnect during feed, end test")
            errorMP = True
        #errorMP = checkForMPDisconnect(mp)
        #print("Time" + str(time.time()- start))
        if time.time()- start > (dist/22):
            break
        await asyncio.sleep(2)

async def vanguardRetractAsync(mp, dist):
    j = {"distance": dist}
    logText("    Retract"+ str(j))
    start = time.time()
    mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
    assert mp_obj is not None
    old_job = mp_obj["job"]
    ignore_timestamp = old_job["time"]["started"] if old_job is not None else None
    errorMP = False
    try:
        post(URL_BASE + "vanguard/retract/" + str(mp), json=j)
    except:
        print("Exception in retract, not of concern")
        #errorMP = True
    while not errorMP:
        mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
        if mp_obj is not None:
            job = mp_obj["job"]
        else:
            logText("Disconnect during feed, end test")
            errorMP = True
        #errorMP = checkForMPDisconnect(mp)
        #print("Time" + str(time.time()- start))
        if time.time()- start > (dist/22):
            break
        await asyncio.sleep(2)

liberty_to_home = wrapLibertyDoJob(LibertyJob("to PX", "liberty/to-home", {"length": 0}, "toHome"))
liberty_to_printhead = wrapLibertyDoJob(LibertyJob("to printhead", "liberty/to-printhead", {"length": 0}, "toPrinthead"))
liberty_to_nozzle = wrapLibertyDoJob(LibertyJob("to nozzle", "liberty/to-nozzle", {"length": 0}, "toNozzle"))
liberty_unload = wrapLibertyDoJob(LibertyJob("unload", "liberty/unload", {"performCut": False, "materialPod": 0, "useOutgoingSwitch": True, "checkLoaded": False}, "unloading"))
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

def _mp_retract_filament(mp, dist):
    return PreparedTimeConsumingTask(VANGUARD_TASK_KIND, (lambda: vanguardRetractAsync(mp, dist)))

def _mp_unload(mp, dist, cutStatus):
    return PreparedTimeConsumingTask(LIBERTY_TASK_KIND, (lambda: unloadMP(mp, dist, cutStatus)))

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


#New functions
#check if the mp is connected
def checkForMPDisconnect(mp) -> bool:   
    mp_obj= getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
    if(mp_obj == "null"):
        logText("MP not connected")
        return True
    
    try:
        valueEnc = instantaneous_task.read_feed_encoder("feed",mp)
        logText("Live Encoder Value: " + str(valueEnc))
    except:
        logText("Cannot read encoder. Potential Disconnect")
        return True
    
    return False
    
_check_for_MPDisconnect = checkForMPDisconnect  

def feedSetDistance(mp, distance) -> bool:
    # feed out a distance 
    if(readVanguardSensor(mp,"outgoing") & readVanguardSensor(mp,"ingoing")):
        time_consuming_task.mp_feed_filament_forward(mp, distance).start_and_wait_til_done()
    else:
        logText("Filament not loaded correctly")
        return True  

    #check for disconnect
    if(checkForMPDisconnect(mp)):
        logText("Disconnect during Feed")
        return True

    return False   

def retractSetDistance(mp, distance):
    #Retract a distance
    if(readVanguardSensor(mp,"outgoing") & readVanguardSensor(mp,"ingoing")):
        time_consuming_task.mp_retract_filament(mp, distance).start_and_wait_til_done()
    else:
        logText("Filament not loaded correctly")
        return True
    
    #check for disconnect
    if(checkForMPDisconnect(mp)):
        logText("Disconnect during retract")
        return True

    return False

def unloadWithCut(mp, distance):
    #Retract a distance
    if(readVanguardSensor(mp,"outgoing") & readVanguardSensor(mp,"ingoing")):
        time_consuming_task.mp_unload(mp, distance, True).start_and_wait_til_done()
    else:
        logText("Filament not loaded correctly")
        return True
    
    #check for disconnect
    if(checkForMPDisconnect(mp)):
        logText("Disconnect during retract")
        return True

    return False

def unloadWithoutCut(mp, distance):
    #Retract a distance
    if(readVanguardSensor(mp,"outgoing") & readVanguardSensor(mp,"ingoing")):
        time_consuming_task.mp_unload(mp, distance, False).start_and_wait_til_done()
    else:
        logText("Filament not loaded correctly")
        return True
    
    #check for disconnect
    if(checkForMPDisconnect(mp)):
        logText("Disconnect during retract")
        return True

    return False

def logText(string):
    print(string)
    #save to csv
    logger.warning(string)


instantaneous_task = SimpleNamespace(
    read_temperatures=_read_temperatures, # takes no args, returns object with properties ".target" and ".actual"
    get_connected_mp_numbers=_get_connected_mp_numbers, # takes no args, returns a tuple of ints
    read_home_switch=_read_home_switch, # takes no args, returns True or False. (True means pressed)
    read_printhead_switch=_read_printhead_switch, # takes no args, returns True or False. (True means pressed)
    clear_printhead_encoder=_clear_printhead_encoder, # takes no args, returns nothing
    read_printhead_encoder=_read_printhead_encoder, # takes no args, returns a float  
    read_feed_encoder=_read_feed_encoder, # takes 2 args, returns a float  
    check_for_MPDisconnect = _check_for_MPDisconnect # takes 2 args, returns a bool
    
)

time_consuming_task = SimpleNamespace(
    # currently none of these return anything after comleting
    to_home=_to_home, # takes mp number
    mp_feed_filament_forward=_mp_feed_filament_forward, # takes mp number and mm distance
    mp_retract_filament=_mp_retract_filament, # takes mp number and mm distance
    mp_unload=_mp_unload, # takes mp number and mm distance
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
    errorStatus = False

    mps = instantaneous_task.get_connected_mp_numbers()
    assert len(mps) > 0, "no MPs connected"
    assert len(mps) < 2, "warning: not meant for test jig multiple MPs connected"
    logText("MPs connected:"+ str(mps))

    #Distances
    CUT_L = 200
    FEED_L = 100
    RETRACT_L= 100
    cycles = 5
    SHORT_FEED_L = 50
    shortFeedDistance = 0
    delayTime = 60 #1 minute
    tolerance = 500

    #Set script type
    scriptType = input("Enter script number (enter help for details): ")
    match scriptType:
        case "1":
            FEED_L = 15000
            RETRACT_L = 15000
            cycles = 29
            delayTime = 120 #2 minutes
        case "2":
            #call third script
            FEED_L = 1500
            RETRACT_L = 1500
            cycles = 115
            tolerance = 200
        case "3":
            FEED_L = 2000
            RETRACT_L = 1200
            cycles = 115
            tolerance = 200
            print("Note that outputted distance will be amount fed")
        case "4":
            FEED_L = 350000
            RETRACT_L = 35000
            cycles = 1
            tolerance = 1000
        case "5":
            FEED_L = 800
            RETRACT_L = 800
            cycles = 10
            tolerance = 100
        case _:
            print("Help: Script details")
            print("1 : long feed/retract 350 000")
            print("2 : feed/retract with cut and short 50 feeds")
            print("3 : standard feed/retract 1500")
            errorStatus = True

    logText("Starting Script " + str(scriptType) + " on " + str(SOM_NAME))

    #Encoder and distance tracking
    startTestEncoder = float(0)
    startEncoder = startTestEncoder
    currentEncoder = startEncoder
    distance = 0
    

    for i in range(cycles):
        if(errorStatus):
            break
        else:
            logText(" ------------------------------------------------------ " )
            logText("Cycles completed:" + str(i))
            logText("Total distance: "+ str( distance))

        for mp in mps:

            # make sure all the MPs we started with are still connected, this will catch power offs where it does not come back
            assert mps == instantaneous_task.get_connected_mp_numbers()
            if(not i):
                #first cycle, log additional data and perform an unload to be safe
                startTestEncoder = instantaneous_task.read_feed_encoder("feed",mp)
                startEncoder = startTestEncoder
                mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
                assert mp_obj is not None
                serialNum = mp_obj["data"]["serialNumber"]
                logText('Testing MP - '+ str(serialNum))
                logText("First encoder reading " + str(startEncoder)) 
                unloadWithoutCut(mp, 1000)               

            #Feed/check for error
            if(feedSetDistance(mp, FEED_L)):
                print("Disconnect")
                errorStatus=True
                break
            else:
                distance = distance + FEED_L
                
                
            #Check for disconnect that was not caught by other checks during feed
            try:
                currentEncoder= instantaneous_task.read_feed_encoder("feed",mp)
                encoderDiff= abs(startEncoder - currentEncoder)
                logText("Current feed encoder "+ str(currentEncoder))
                logText("Difference in encoder " + str(encoderDiff))
                if(encoderDiff < (FEED_L- 1000)):
                    logText("Something went wrong, potential quick disconnect. Encoder diff:" + str(encoderDiff) )
                    errorStatus = True
            except:
                print("timeout, ignore")
            time.sleep(2)
            
            if scriptType == "3":
                #Perform short feeds
                while shortFeedDistance < CUT_L:
                    if(feedSetDistance(mp, SHORT_FEED_L )):
                        print("Disconnect")
                        errorStatus=True
                        break
                    else:
                        distance = distance + SHORT_FEED_L 
                        shortFeedDistance = shortFeedDistance + SHORT_FEED_L 
                
                #Retract with cut/check for error
                if(unloadWithCut(mp, RETRACT_L)):
                    logText("disconnect")
                    errorStatus= True
                    break
                
                #reset variables and wait
                currentEncoder= instantaneous_task.read_feed_encoder("feed",mp)
                startEncoder = currentEncoder
                shortFeedDistance = 0
                logText("Completed cycle. Delay " +str(delayTime) + " seconds")
                time.sleep(delayTime)
            elif scriptType == "1":
                #no retract, just wait 
                currentEncoder= instantaneous_task.read_feed_encoder("feed",mp)
                startEncoder = currentEncoder
                logText("Completed cycle. Delay " +str(delayTime) + " seconds")
                time.sleep(delayTime)
            else:
                #Retract/check for error
                if(unloadWithoutCut(mp, RETRACT_L)):
                    logText("disconnect")
                    errorStatus= True
                    break
                else:
                    distance = distance + RETRACT_L
                
                #Check for disconnect that was not caught by other checks
                try:
                    currentEncoder= instantaneous_task.read_feed_encoder("feed",mp)
                    encoderDiff= abs(startEncoder - currentEncoder)
                    logText("Current feed encoder "+ str(currentEncoder))
                    logText("Difference in encoder " + str(encoderDiff))
                    if(encoderDiff > 100):
                        logText("Something went wrong, potential quick disconnect. Encoder diff:" + str(encoderDiff) )
                        errorStatus = True
                except:
                    print("timeout, ignore")
                startEncoder = currentEncoder
                logText("Completed cycle. Delay " +str(delayTime) + " seconds")
                time.sleep(delayTime)
                
            
    if(errorStatus):
        logText("Failed")
    else:
        logText("Passed")
        logText("Total Slip/Skip = " + str(abs(startEncoder - startTestEncoder)))

    logText("End distance = "+ str(distance))           

                

if __name__ == "__main__":
    main()
