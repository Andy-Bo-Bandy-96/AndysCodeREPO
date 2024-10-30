# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 3:36:36 2023

@author: Andrew
"""
from requests import Session, ConnectionError
import time
import json

s = Session()
ID = 'changeme-f8dc7ab00fce'
URL_BASE = f'http://{ID}.local:4030/'
POST_FEED = URL_BASE + 'Vanguard/feed/0'
REQUEST_STATE = URL_BASE + 'Vanguard/state'


def request(fn, *args, **kwargs):
    RETRY_DELAY = 1
    while True:
        try:
            res = fn(*args, **kwargs)
            res.raise_for_status()  # Raises HTTPError for bad responses
        except (ConnectionError, requests.HTTPError) as e:
            print(f"Connection issue: {e}. Retrying in {RETRY_DELAY} seconds.")
            time.sleep(RETRY_DELAY)
        else:
            return res


def get(*args, **kwargs):
    return request(s.get, *args, **kwargs).json()


def post(*args, **kwargs):
    return request(s.post, *args, **kwargs)


def switchState():
    try:
        state = get(REQUEST_STATE)
        return state['materialPods'][0]['data']['sensors'][1]['value']
    except KeyError:
        return 'unknown'  # Handle unexpected response structure


def post_retract(distance):
    POST_RETRACT = URL_BASE + 'Vanguard/retract/0'
    return post(POST_RETRACT, json={'distance': distance})


def main():
    RETRIES = 100
    WAIT_T = 0.3
    RETRY_L = 3.5
    TRY_L = 3.5
    
    cycleCount = 0
    retry = 0
    
    while True:
        cycleCount += 1
        current_state = switchState()
        
        if current_state == 'low':
            post(POST_FEED, json={'distance': TRY_L})
            time.sleep(WAIT_T)
            retry = 0
            
            while retry < RETRIES and switchState() == 'low':
                retry += 1
                post(POST_FEED, json={'distance': RETRY_L})
                time.sleep(WAIT_T)
                
            post(POST_FEED, json={'distance': 3})
            time.sleep(WAIT_T)
        else:
            print(cycleCount, retry, 'FAIL TO UNLOAD/STUCK')
            break
        
        print(cycleCount, 'FIRST PRINT')
        current_state = switchState()
        if current_state == 'high':
            pass  # Save cycle count or other actions here
        else:
            print(cycleCount, retry, 'FAIL to depress')
        
        # Perform the retraction and retry if necessary
        post_retract(TRY_L)
        time.sleep(WAIT_T)
        retry = 0
        
        while retry < RETRIES and switchState() == 'high':
            retry += 1
            post_retract(RETRY_L)
            time.sleep(WAIT_T)
        
        post_retract(3.5)
        time.sleep(WAIT_T)
        print(cycleCount, 'Second PRINT')


if __name__ == "__main__":
    main()
