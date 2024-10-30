# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 3:36:36 2023

@author: Andrew
"""
from requests import Request, Session, ConnectionError
import os
import time
import json
import sys

s = Session()
#get('http://abcd-el.local:4030/state')
#print(get(REQUEST_STATE)['materialPods'][7]['data']['sensors'])
# ^ list, [0] = button, [1] = outgoing, [2] = ingoing
ID = 'changeme-f8dc7ab00fce'
URL_BASE = f'http://{ID}.local:4030/'
POST_FEED = URL_BASE + 'Vanguard/feed/0'
POST_UNLOAD = URL_BASE + 'liberty/unload'
REQUEST_STATE = URL_BASE + 'Vanguard/state'


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
    assert res.ok, res.text
    return res

def get(*args, **kwargs):
    return request(s.get, *args, **kwargs).json()

def post(*args, **kwargs):
    time.sleep(0)
    return request(s.post, *args, **kwargs)

def switchState(mp = 8, switch = 1):
    # switch: [0] = button, [1] = outgoing, [2] = ingoing
    return(get(REQUEST_STATE)['materialPods'][0]['data']['sensors'][1]['value'])

##def switchState(mp=8, switch=1):
    try:
        data = get(REQUEST_STATE)
        if data is None:
            raise ValueError("get(REQUEST_STATE) returned None.")
        
        # Debugging: Print the data structure for inspection
        #print(json.dumps(data, indent=2))
        
        # Check if 'materialPods' exists and has at least 8 items
        if 'materialPods' not in data or len(data['materialPods']) <= 7:
            raise KeyError("'materialPods' key is missing or does not have enough items.")
        
        # Check the 8th item (index 7) in 'materialPods'
        material_pod = data['materialPods'][0]
        if material_pod is None:
            raise ValueError("The item at index 7 in 'materialPods' is None.")
        
        # Check if 'data' and 'sensors' exist in the material pod
        if 'data' not in material_pod or 'sensors' not in material_pod['data']:
            raise KeyError("'data' or 'sensors' key is missing in the material pod.")
        
        sensors = material_pod['data']['sensors']
        
        # Find the sensor with name 'outgoing'
        outgoing_sensor = next((sensor for sensor in sensors if sensor['name'] == 'outgoing'), None)
        if outgoing_sensor is None:
            raise KeyError("'outgoing' sensor not found in 'sensors'.")
        
        # Return the value of the 'outgoing' sensor
        return outgoing_sensor['value']
    
    except Exception as e:
        print(f"Error in switchState: {e}")
        raise
    
    except Exception as e:
        print(f"Error in switchState: {e}")
        raise

##def writeFail(myfile, failID):
    if failID == 0:
        myfile.write('\nFAIL TO UNLOAD FILAMENT OR FILAMENT SWITCH IS STUCK\n')
    elif failID == 1:
        myfile.write('\nFAIL TO DEPRESS SWITCH OR FILAMENT NOT DETECTED\n')
    myfile.write(json.dumps(get(REQUEST_STATE)))
    myfile.flush()
    os.fsync(myfile.fileno())
    sys.exit(1)
    

def main():
    ##mypath = r'C:\Users\Andre\OneDrive\Desktop\MaterialPodTestingScripts\Magnet Switch Test Aug 2024'
    ##filename = r'\test.txt'
    
    ##mypath = 'testdata'
   ##try: 
        ##os.mkdir(mypath)
    ##except: 
      ##  pass
    ##filename = 'Switch Test Log.txt'
    ##myfile = open(os.path.join(mypath, filename), "w")
    
    
    #switch = get(REQUEST_STATE)['materialPods'][7]['data']['sensors'][1]['value']
    RETRIES = 120
    cycleCount = 0
    WAIT_T = 0.3
    WAIT_T_i = 0.3
    retry = 0
    TRY_L = 3.5
    RETRY_L = 3.5
        
    while True:
        cycleCount += 1
        if (switchState() == 'high'):
            ##if cycleCount > 1:
                #print(retry)
                ##myfile.write(f', pull retry = {retry}mm\n')
                ##myfile.flush()
                ##os.fsync(myfile.fileno())
            ##print(switchState())
            post(POST_UNLOAD, json = {'performCut':0,'materialPod':0,'useOutgoingSwitch':True, 'checkLoaded':False})


#%%
if __name__ == "__main__":
    main()
