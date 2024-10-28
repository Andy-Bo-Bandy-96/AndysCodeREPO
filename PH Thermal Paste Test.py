import requests
from requests import Session, ConnectionError
import time
import sys

URL_BASE = "http://" + "fowx-el" + ".local:4030/"
s = Session()
j = {"commands": [
"M104 S470",
"M140 S120",
"M141 S80",
]}

def main():
    for i in range(120):
        print(i)
        streamFromGcode(j)
        print("Sleeping for 60 seconds")
        time.sleep(60)
         # Fetching data from URL

def streamFromGcode(j) -> None:
    post(URL_BASE + "streamFromCommands", json=j)

def check_status() -> bool:
    max_retries = 3
    for _ in range(max_retries):
        try:
            # Check URL_BASE + "firmwareCom/printhead/data"
            printhead_response = requests.get(URL_BASE + "firmwareCom/printhead/data")
            if printhead_response.status_code == 200:
                print("Printhead data URL checked successfully.")
                return True  # Return True if both checks pass
            else:
                print(f"Failed to fetch data from URL: {URL_BASE}firmwareCom/printhead/data. Status code: {printhead_response.status_code}")
                return False
        except requests.ConnectionError as e:
            print(f"Connection error: {e}")
        time.sleep(5)  # Add a delay before retrying
    return False

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