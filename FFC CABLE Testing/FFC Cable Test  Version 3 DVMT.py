import requests
from requests import Session, ConnectionError
import time
import sys

URL_BASE = "http://" + "dvmt-ela" + ".local:4030/"
s = Session()
j = {"commands": [
"M104 S280",
"M203 X400 Y400",
"M204 T3000 P1000 R1500",
"G28 X Y",
"M201 X10000 Y10000",
"M204 T10000",
"M104 S280",
"M109 S280 T0"
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"M104 S280",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y8",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X350 Y350",
"G1 E0.5 F150"
"G1 X8 Y8 F30000",
"G1 X350 Y350",
"G1 X8 Y350",
"G1 X350 Y8",
"G1 X8 Y350",
"G1 X8 Y8",
"G1 X350 Y8",
"G1 X350 Y350",
"",
"G1 X177.5 Y177.5",
"M84",
"M201 X5000 Y5000",
"M204 T3000 P1000",
]}

def main():
    for i in range(10000):
        print(i)
        streamFromGcode(j)
        time.sleep(355)
        retry_count = 3
        while retry_count > 0:
            if check_status():
                break
            else:
                print(f"Retrying check_status() at cycle {i}...")
                retry_count -= 1
                if retry_count > 0:
                    time.sleep(20)  # 20-second delay between retry attempts
        else:
            print(f"Failed at cycle: {i}")  # Print failure message if retries exhausted
            break  # Break out of the loop if retries exhausted
        streamFromGcode({"commands": ["M920 X125"]})
        time.sleep(5)

def streamFromGcode(j) -> None:
    post(URL_BASE + "streamFromCommands", json=j)

def check_status() -> bool:
    response = requests.get(URL_BASE + "firmwareCom/printhead/data")
    if response.status_code == 200:
        return True
    else:
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