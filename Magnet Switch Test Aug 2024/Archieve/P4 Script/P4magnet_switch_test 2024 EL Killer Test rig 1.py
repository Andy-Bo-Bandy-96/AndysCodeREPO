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
import csv  # Import CSV module
from datetime import datetime  # Import datetime for timestamping

s = Session()
#get('http://abcd-el.local:4030/state')
#print(get(REQUEST_STATE)['materialPods'][7]['data']['sensors'])
# ^ list, [0] = button, [1] = outgoing, [2] = ingoing
ID = 'mosaic-mp-aqua-rig-1'
URL_BASE = f'http://{ID}.local:4030/'
POST_FEED = URL_BASE + 'Vanguard/feed/0'
REQUEST_STATE = URL_BASE + 'Vanguard/state'

# Setup logging
log_file = 'log.csv'
with open(log_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Timestamp', 'Cycle Count', 'Retry Count', 'Message'])

def log(cycle_count, retry, message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - Cycle: {cycle_count}, Retry: {retry}, Message: {message}")
    with open(log_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, cycle_count, retry, message])

def request(fn, *args, **kwargs):
    for _ in range(1000):  # Try 1000 times before giving up
        try:
            res = fn(*args, **kwargs)
            if res.ok:
                return res
            else:
                print(f"Request failed with status code {res.status_code}. Retrying...")
                time.sleep(1)
        except ConnectionError:
            print(f"Connection issue. Retrying IMMEDIATELY")
            time.sleep(1)
    assert res.ok, res.text  # If all retries fail


def get(*args, **kwargs):
    return request(s.get, *args, **kwargs).json()

def post(*args, **kwargs):
    time.sleep(0.1)
    return request(s.post, *args, **kwargs)

def switchState(mp = 8, switch = 1):
    # switch: [0] = button, [1] = outgoing, [2] = ingoing
    return(get(REQUEST_STATE)['materialPods'][0]['data']['sensors'][1]['value'])
    

def main():
    RETRIES = 1000000
    cycleCount = 0
    WAIT_T = 20
    WAIT_T_i = 0.4
    retry = 0
    TRY_L = 3.5
    RETRY_L = 3.5
        
    while True:
        cycleCount += 1
        if (switchState() == 'low'):
            post(POST_FEED, json = {'distance':200})
            time.sleep(WAIT_T)
            retry = 0
            #switch = get(REQUEST_STATE)['materialPods'][0]['data']['sensors'][1]['value']
            while (retry < RETRIES) and (switchState() == 'low'):
                retry += 3.5
                post(POST_FEED, json = {'distance':RETRY_L})
                time.sleep(WAIT_T_i)
                # may want to add a wait after the last retry if filament switch is laggy
            time.sleep(WAIT_T_i)
        else:
            log(cycleCount, retry, 'FAIL TO UNLOAD/STUCK')
            ##writeFail(myfile, 0)
            break
            
        log(cycleCount, retry, 'After Feed')
        if switchState() == 'high': 
            #save cycle count & 
            pass
        else:
            log(cycleCount, retry, 'FAIL to depress')
            break

        
        POST_RETRACT = URL_BASE + 'Vanguard/retract/0'
        post(POST_RETRACT, json = {'distance':190})
        time.sleep(WAIT_T)
        ##print(WAIT_T)
        retry = 0
        #switch = get(REQUEST_STATE)['materialPods'][0]['data']['sensors']['value']
        while (retry < RETRIES) and (switchState() == 'high'):
            retry += 3.5
            post(POST_RETRACT, json = {'distance':RETRY_L})
            time.sleep(WAIT_T_i)
                # may want to add a wait after the last retry if filament switch is laggy
        post(POST_RETRACT, json = { 'distance':3.5}) # move by extra mm to ensure switch press not coincidence
        time.sleep(WAIT_T_i)
        log(cycleCount, retry, 'Completed Successfully ')
#%%
if __name__ == "__main__":
    main()
