# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 15:27:40 2023

@author: Daniel
"""

from requests import Session, ConnectionError
import time
from itertools import count
from typing import NamedTuple
import os
import sys

URL_BASE = "http://or44-el.local:4030/"
s = Session()

def request(fn, *args, **kwargs):
    while True:
        try:
            res = fn(*args, **kwargs)
        except ConnectionError:
            RETRY_DELAY = 1
            print(f"Connection issue. Retrying in {RETRY_DELAY} seconds.")
            time.sleep(RETRY_DELAY)
        else:
            break
    #print(res.ok, res.text)
    assert res.ok, res.text
    return res

def get(*args, **kwargs):
    return request(s.get, *args, **kwargs).json()

def put(*args, **kwargs):
    request(s.put, *args, **kwargs)

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

def extrude(mm, myfile = None, RATE = int(100), wait = True):
    #RATE = 300
    j = {"commands": ["M83", f"G1 F{RATE} E{mm}"]}
    if myfile: print2file(myfile, f"extrude G1 F{RATE} E{mm}")
    post(URL_BASE + "streamFromCommands", json=j)
    if (wait): 
        time.sleep(abs(mm) / RATE * 60 * 1.01 + 0.5)
    else:
        return(abs(mm) / RATE * 60 * 1.01 + 0.5)

def vanguardFeed(mp, dist, myfile, wait = True):
    j = {"distance": dist}
    print2file(myfile, f"feed {j}")
    mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
    assert mp_obj is not None
    old_job = mp_obj["job"]
    ignore_timestamp = old_job["time"]["started"] if old_job is not None else None
    post(URL_BASE + f"vanguard/feed/{mp}", json=j)
    
    if wait == False:
        return(0)
    
    while True:
        mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
        assert mp_obj is not None
        job = mp_obj["job"]
            
        #assert job is not None and job["name"] == "feeding", job
        if job["time"]["started"] != ignore_timestamp and job["finished"]:
            break
        time.sleep(0.2)

def vanguardRetract(mp, dist, myfile):
    j = {"distance": dist}
    print2file(myfile, f"retract {j}")
    mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
    assert mp_obj is not None
    old_job = mp_obj["job"]
    ignore_timestamp = old_job["time"]["started"] if old_job is not None else None
    post(URL_BASE + f"vanguard/retract/{mp}", json=j)
    while True:
        mp_obj = getState()["data"]["liberty"]["data"]["vanguard"]["materialPods"][mp]
        assert mp_obj is not None
        job = mp_obj["job"]
        #assert job is not None and job["name"] == 'retracting', job
        if job["time"]["started"] != ignore_timestamp and job["finished"]:
            break
        time.sleep(0.2)

def getPrintheadEncoderCount() -> float:
    return get(URL_BASE + "firmwareCom/printhead/encoderDistance")

def deletePrintheadEncoderCount() -> None:
    delete(URL_BASE + "firmwareCom/printhead/encoderDistance")
    
def testEncoderCount(TO_EXTRUDE = 10, RATE = 115):
    deletePrintheadEncoderCount()
    time.sleep(1)
    extrude(TO_EXTRUDE, RATE = RATE)
    time.sleep(1)
    extruded = getPrintheadEncoderCount()
    print(extruded)
    return(TO_EXTRUDE, extruded)

to_home = wrapDoJob(Job("to PX", "liberty/to-home", {"length": 0}, "toHome"))
to_printhead = wrapDoJob(Job("to printhead", "liberty/to-printhead", {"length": 0}, "toPrinthead"))
to_nozzle = wrapDoJob(Job("to nozzle", "liberty/to-nozzle", {"length": 0}, "toNozzle"))
unload = wrapDoJob(Job("unload", "liberty/unload", {"length": 0, "performCut": False, "useOutgoingSwitch": True, "checkLoaded":False}, "unloading"))
cut = wrapDoJob(Job("cut", "liberty/cut", {}, "cutting"))

def print2file(myfile, val):
    myfile.write(val+'\n')
    myfile.flush()
    os.fsync(myfile.fileno())

def to_nozzle_hack2(i, myfile, materialPod: int, CUT_L) -> None:
    print2file(myfile, "-- special safe nozzle load 2 beginning --")    
    SWITCH2ENCODER = 40 #tbh when I measured, should be 17mm, but OK w/e
    ENCODER2DRIVE = 50#mm
    MAX_TRIES = 15 # ATTENTION ANDREW
    SF_L = 5 #mm, safety factor length
    MP_FR = 50 # steps/s  # ATTENTION ANDREW
    PH_FR = 115 # mm/min  # ATTENTION ANDREW
    
    
    MP_shuffle = 14
    PH_shuffle = 20
    put(URL_BASE + "vanguard/feedRate", json={"speed":MP_FR}) #speed given in steps/s. Conversion to mm/min = *60/16.976525
    deletePrintheadEncoderCount()
    encVal = getPrintheadEncoderCount()
    vanguardFeed(materialPod, SWITCH2ENCODER, myfile) #changed from 34
    assert readCascadeSensor("printHead")
    lv1 = 0
    while (ENCODER2DRIVE + SF_L > encVal):
        dT = extrude(PH_shuffle, myfile, RATE = PH_FR, wait = False)
        t_start = time.time()
        vanguardFeed(materialPod, MP_shuffle, myfile)
        t_end = time.time()
        t_wantEnd = t_start+dT
        if t_end < t_wantEnd:
            time.sleep(t_wantEnd-t_end)
        encVal = getPrintheadEncoderCount()
        print2file(myfile, str(encVal))
        if lv1 > MAX_TRIES:
            myfile.write('\nNozzleLoadFailure\n')
            myfile.flush()
            os.fsync(myfile.fileno())
            myfile.close()
            sys.exit(1)
        lv1+=1
    put(URL_BASE + "vanguard/feedRate", json={"speed":500})
    print2file(myfile, "-- special safe nozzle load finished --")
    

# =============================================================================
# def to_nozzle_hack(i, myfile, materialPod: int, CUT_L) -> None:
#     print2file(myfile, "-- special safe nozzle load beginning --")
#     SWITCH2ENCODER = 28
#     MP_FR = 22 # steps/s
#     PH_FR = 100 # mm/min
#     vanguardFeed(materialPod, SWITCH2ENCODER, myfile) #changed from 34
#     assert readCascadeSensor("printHead")
#     put(URL_BASE + "vanguard/feedRate", json={"speed":MP_FR}) #speed given in steps/s. Conversion to mm/min = *60/16.976525
#     MP_shuffle = 14
#     PH_shuffle = 20
#     check_L = 10
#     check_r = 0.8
#     lv1 = 0
#     while True:
#         print2file(myfile, str(i))
#         #maybe should add a sleep here to ensure that any springiness
#         deletePrintheadEncoderCount()
#         if lv1 == 0:
#             for lv2 in range(5):
#                 tempVar = getPrintheadEncoderCount()
#                 print(tempVar)
#                 myfile.write('PH encoder: '+str(tempVar)+'\n')
#                 time.sleep(0.5)
#             
#         extrude(check_L, myfile, RATE = PH_FR)
#         
#         tempVar = getPrintheadEncoderCount()
#         print(tempVar)
#         myfile.write('PH encoder: '+str(tempVar)+'\n')
#         if tempVar >= check_r:
#             break
#         dT = extrude(PH_shuffle, myfile, RATE = PH_FR, wait = False)
#         t_start = time.time()
#         vanguardFeed(materialPod, MP_shuffle, myfile)
#         t_end = time.time()
#         t_wantEnd = t_start+dT
#         if t_end < t_wantEnd:
#             time.sleep(t_wantEnd-t_end)
#         if lv1 > (CUT_L/MP_shuffle + 2): #+2 is somewhat arbitrary, just some extra
#             myfile.write('\nNozzleLoadFailure\n')
#             myfile.flush()
#             os.fsync(myfile.fileno())
#             myfile.close()
#             sys.exit(1)
#         lv1 += 1
#     put(URL_BASE + "vanguard/feedRate", json={"speed":500})
#     print2file(myfile, "-- special safe nozzle load finished --")
# =============================================================================

def main():
    
    mypath = 'testdata'
    try: 
        os.mkdir(mypath)
    except: 
        pass
    filename = 'filamentLoadingTest.txt'
    myfile = open(os.path.join(mypath, filename), "w")
    
    MP_FAST = 1000
    MP_NORM = 500
    
    put(URL_BASE + "vanguard/feedRate", json={"speed":MP_FAST})
    to_nozzle_implementation = to_nozzle_hack2

    #temperatures = getState()["data"]["apollo"]["context"]["temperatures"]["nozzle"]
    #assert temperatures["target"] >= 200 and temperatures["actual"] >= 200, temperatures

    mps = getMpNumbers()
    assert len(mps) > 0, "no MPs connected"
    print2file(myfile, f"MPs connected: {mps}")
    
    
# =============================================================================
#     if input("proceed? (y/n) ").strip().lower() != "y":
#         return
# =============================================================================

    # for mp in mps:
    #     print2file(myfile, mp, readVanguardSensor(mp, "outgoing"))
    #     if readVanguardSensor(mp, "outgoing"):
    #         assert mps == getMpNumbers()
    #         unload(materialPod=mp)
    for i in count(0):
        CUT_L = int((1 + i%10)*100)

        print2file(myfile, f"cycles done: {i}")

        for mp in mps:
            assert mps == getMpNumbers()

            mpd = {"materialPod": mp}
            print2file(myfile, f'"materialPod": {mp}')
            
            put(URL_BASE + "vanguard/feedRate", json={"speed":MP_FAST})
            to_home(**mpd)
            assert readCascadeSensor("filamentHome")
            print2file(myfile, 'filament reached PX home')
            put(URL_BASE + "vanguard/feedRate", json={"speed":MP_NORM})
            
# =============================================================================
#             vanguardFeed(mp, CUT_L, myfile)
#             cut()
#             print2file(myfile, 'cut finished')
#             
#             vanguardFeed(mp, 5, myfile)
#             print2file(myfile, 'pushed 5mm')
#             vanguardRetract(mp, 10, myfile)
#             print2file(myfile, 'retracted 10mm')
# =============================================================================
            to_printhead(**mpd)
            print2file(myfile, 'to printhead finished')
            
            to_nozzle_implementation(i, myfile, **mpd, CUT_L = CUT_L)
            print2file(myfile, 'to nozzle finished')
            
            if (i%10 == 9):  # ATTENTION ANDREW, note 2nd # is 1 smaller than 1st number since indexed to 0
                cut()
                numExtrudes = 0
                while readCascadeSensor("printHead"):
                    extrude(100, myfile, RATE = 3000) # for longer test
                    if numExtrudes > 20:
                        myfile.write('\nNozzleLoadFailure\n')
                        myfile.flush()
                        os.fsync(myfile.fileno())
                        myfile.close()
                        sys.exit(1)
                    numExtrudes += 1
                dT = extrude(75, myfile, RATE = 3000, wait = False)
                t_start = time.time()
                time.sleep(1)
                unload(**mpd)
                t_end = time.time()
                t_wantEnd = t_start+dT
                if t_end < t_wantEnd:
                    time.sleep(t_wantEnd-t_end)
                print2file(myfile, 'extrude finished')
            else:
                extrude(-199, RATE = 700, wait = False) #rate should be ~ 200*60/16.976525 ~=706
                vanguardRetract(mp, 199, myfile)
                #distance retracted should be >= MAX_TRIES*MP_SHUFFLE (from nozzleLoad2 function)
                # here just do 199 since its the max extrusion distance in 1 go
                unload(**mpd) 
                print2file(myfile, 'filament unloaded')

if __name__ == "__main__":
    main()
