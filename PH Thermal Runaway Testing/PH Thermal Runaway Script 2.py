import requests
from requests import Session, ConnectionError
import time
import sys

## Replace Fowx-el with the name of the printer you want this to run on 

URL_BASE = "http://" + "fowx-el" + ".local:4030/"
s = Session()

##Replace the g-code inside the brackets with what you hope to run. Please note each line of G-code must be between " " with a , at the end of every line
T = {"commands": [
"M104 S490",
"M140 S120",
"M141 S80",
"M141 S80",
]}
j = {"commands": [
"",
"",
"",
]}

def main():
    streamFromGcode(T)
    for i in range(12600): ## i is the number of cycles this script will run. So for example this script runs 120 times 
        print(i)
        streamFromGcode(j)
        time.sleep(1) #This value is critical. This sets how often the script will re-send the G-code command 
        ## This value needs to match the length of time it takes to run through all the lines of G-Code found in j. This might need to be timed manually
        ## For the first time to set the value correctly. It is currently set to 60, for a script that take 60 Seconds to run 

def streamFromGcode(j) -> None:
    post(URL_BASE + "streamFromCommands", json=j)

def post(url, *args, **kwargs):
    request(s.post, url, *args, **kwargs)

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

main()