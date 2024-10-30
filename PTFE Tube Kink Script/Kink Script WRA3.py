# -*- coding: utf-8 -*-
"""
Created on Wed Oct  4 09:58:52 2023
@author: Daniel

Motivation:
    - noticed that gantry resistance dropped significantly on O1 after running 
    beltBurnIn.py. Hypothesize due to lubricant being spread out
    - tested on 2 Pilot printers:
        - 1 previously false homed, other was fine but rails needed to be
        cleaned due to accumulation of dirt on gantry
        - both printers false homed during 2nd Y home prior to script
        - after 2x big zig zag squares + 2x small zig zag squares, no false
        homing was observed
Usage:
    run script from a device connected to the same network as the printer
    script can be run directly on the printer by uploading the script & running
    once a ssh connection has been established.
        python3 distributeLubricant.py <printer SKU>
    eg. python3 distributeLubricant.py dvmt-ela
    Recommended usage involves using 'nohup' and '&' as well, to ensure network
    drops do not affect the test and to allow for the CLI to remain usable
    during the test:
        nohup python3 distributeLubricant.py <printer SKU> &
    eg. nohup python3 distributeLubricant.py dvmt-ela &
    Script can also be run from an IDE (instead of a CLI as per above)
    Note: ensure that the requests library is installed on the deviec that is
        running the test
Conclusion of testing/outcome:
    - TBD based on testing at Microart
"""


from requests import Session, ConnectionError
import time
import sys

URL_BASE = "http://" + "wra3-el" + ".local:4030/"
s = Session()
j = {"commands": [
"M201 X5000 Y5000",
"M204 T3000 P1000 R1500",
"G28 X Y",
"M201 X10000 Y10000",
"M204 T10000",
"G1 X8.535499999999999 Y8.535499999999999 F18000",
"G1 X12.071 Y15.606",
"G1 X8.535 Y8.535",
"G1 X5.0 Y22.678",
"G1 X12.071 Y15.606",
"G1 X12.071 Y29.748",
"G1 X5.0 Y22.678",
"G1 X5.0 Y36.82",
"G1 X12.071 Y29.748",
"G1 X12.071 Y43.89",
"G1 X5.0 Y36.82",
"G1 X5.0 Y50.962",
"G1 X12.071 Y43.89",
"G1 X12.071 Y58.032",
"G1 X5.0 Y50.962",
"G1 X5.0 Y65.104",
"G1 X12.071 Y58.032",
"G1 X12.071 Y72.174",
"G1 X5.0 Y65.104",
"G1 X5.0 Y79.246",
"G1 X12.071 Y72.174",
"G1 X12.071 Y86.316",
"G1 X5.0 Y79.246",
"G1 X5.0 Y93.388",
"G1 X12.071 Y86.316",
"G1 X12.071 Y100.458",
"G1 X5.0 Y93.388",
"G1 X5.0 Y107.53",
"G1 X12.071 Y100.458",
"G1 X12.071 Y114.6",
"G1 X5.0 Y107.53",
"G1 X5.0 Y121.672",
"G1 X12.071 Y114.6",
"G1 X12.071 Y128.742",
"G1 X5.0 Y121.672",
"G1 X5.0 Y135.813",
"G1 X12.071 Y128.742",
"G1 X12.071 Y142.884",
"G1 X5.0 Y135.813",
"G1 X5.0 Y149.955",
"G1 X12.071 Y142.884",
"G1 X12.071 Y157.026",
"G1 X5.0 Y149.955",
"G1 X5.0 Y164.097",
"G1 X12.071 Y157.026",
"G1 X12.071 Y171.168",
"G1 X5.0 Y164.097",
"G1 X5.0 Y178.24",
"G1 X12.071 Y171.168",
"G1 X12.071 Y185.31",
"G1 X5.0 Y178.24",
"G1 X5.0 Y192.382",
"G1 X12.071 Y185.31",
"G1 X12.071 Y199.452",
"G1 X5.0 Y192.382",
"G1 X5.0 Y206.524",
"G1 X12.071 Y199.452",
"G1 X12.071 Y213.594",
"G1 X5.0 Y206.524",
"G1 X5.0 Y220.666",
"G1 X12.071 Y213.594",
"G1 X12.071 Y227.736",
"G1 X5.0 Y220.666",
"G1 X5.0 Y234.808",
"G1 X12.071 Y227.736",
"G1 X12.071 Y241.878",
"G1 X5.0 Y234.808",
"G1 X5.0 Y248.95",
"G1 X12.071 Y241.878",
"G1 X12.071 Y256.02",
"G1 X5.0 Y248.95",
"G1 X5.0 Y263.092",
"G1 X12.071 Y256.02",
"G1 X12.071 Y270.162",
"G1 X5.0 Y263.092",
"G1 X5.0 Y277.234",
"G1 X12.071 Y270.162",
"G1 X12.071 Y284.304",
"G1 X5.0 Y277.234",
"G1 X5.0 Y291.376",
"G1 X12.071 Y284.304",
"G1 X12.071 Y298.446",
"G1 X5.0 Y291.376",
"G1 X5.0 Y305.518",
"G1 X12.071 Y298.446",
"G1 X12.071 Y312.588",
"G1 X5.0 Y305.518",
"G1 X5.0 Y319.66",
"G1 X12.071 Y312.588",
"G1 X12.071 Y326.73",
"G1 X5.0 Y319.66",
"G1 X5.0 Y333.802",
"G1 X12.071 Y326.73",
"G1 X8.535499999999999 Y346.4645",
"G4 P0",
"",
"G1 X8.535499999999999 Y8.535499999999999 F18000",
"G1 X12.071 Y15.606",
"G1 X8.535 Y8.535",
"G1 X5.0 Y22.678",
"G1 X12.071 Y15.606",
"G1 X12.071 Y29.748",
"G1 X5.0 Y22.678",
"G1 X5.0 Y36.82",
"G1 X12.071 Y29.748",
"G1 X12.071 Y43.89",
"G1 X5.0 Y36.82",
"G1 X5.0 Y50.962",
"G1 X12.071 Y43.89",
"G1 X12.071 Y58.032",
"G1 X5.0 Y50.962",
"G1 X5.0 Y65.104",
"G1 X12.071 Y58.032",
"G1 X12.071 Y72.174",
"G1 X5.0 Y65.104",
"G1 X5.0 Y79.246",
"G1 X12.071 Y72.174",
"G1 X12.071 Y86.316",
"G1 X5.0 Y79.246",
"G1 X5.0 Y93.388",
"G1 X12.071 Y86.316",
"G1 X12.071 Y100.458",
"G1 X5.0 Y93.388",
"G1 X5.0 Y107.53",
"G1 X12.071 Y100.458",
"G1 X12.071 Y114.6",
"G1 X5.0 Y107.53",
"G1 X5.0 Y121.672",
"G1 X12.071 Y114.6",
"G1 X12.071 Y128.742",
"G1 X5.0 Y121.672",
"G1 X5.0 Y135.813",
"G1 X12.071 Y128.742",
"G1 X12.071 Y142.884",
"G1 X5.0 Y135.813",
"G1 X5.0 Y149.955",
"G1 X12.071 Y142.884",
"G1 X12.071 Y157.026",
"G1 X5.0 Y149.955",
"G1 X5.0 Y164.097",
"G1 X12.071 Y157.026",
"G1 X12.071 Y171.168",
"G1 X5.0 Y164.097",
"G1 X5.0 Y178.24",
"G1 X12.071 Y171.168",
"G1 X12.071 Y185.31",
"G1 X5.0 Y178.24",
"G1 X5.0 Y192.382",
"G1 X12.071 Y185.31",
"G1 X12.071 Y199.452",
"G1 X5.0 Y192.382",
"G1 X5.0 Y206.524",
"G1 X12.071 Y199.452",
"G1 X12.071 Y213.594",
"G1 X5.0 Y206.524",
"G1 X5.0 Y220.666",
"G1 X12.071 Y213.594",
"G1 X12.071 Y227.736",
"G1 X5.0 Y220.666",
"G1 X5.0 Y234.808",
"G1 X12.071 Y227.736",
"G1 X12.071 Y241.878",
"G1 X5.0 Y234.808",
"G1 X5.0 Y248.95",
"G1 X12.071 Y241.878",
"G1 X12.071 Y256.02",
"G1 X5.0 Y248.95",
"G1 X5.0 Y263.092",
"G1 X12.071 Y256.02",
"G1 X12.071 Y270.162",
"G1 X5.0 Y263.092",
"G1 X5.0 Y277.234",
"G1 X12.071 Y270.162",
"G1 X12.071 Y284.304",
"G1 X5.0 Y277.234",
"G1 X5.0 Y291.376",
"G1 X12.071 Y284.304",
"G1 X12.071 Y298.446",
"G1 X5.0 Y291.376",
"G1 X5.0 Y305.518",
"G1 X12.071 Y298.446",
"G1 X12.071 Y312.588",
"G1 X5.0 Y305.518",
"G1 X5.0 Y319.66",
"G1 X12.071 Y312.588",
"G1 X12.071 Y326.73",
"G1 X5.0 Y319.66",
"G1 X5.0 Y333.802",
"G1 X12.071 Y326.73",
"G1 X8.535499999999999 Y346.4645",
"G4 P0",
"",
"G1 X8.535499999999999 Y8.535499999999999 F18000",
"G1 X12.071 Y15.606",
"G1 X8.535 Y8.535",
"G1 X5.0 Y22.678",
"G1 X12.071 Y15.606",
"G1 X12.071 Y29.748",
"G1 X5.0 Y22.678",
"G1 X5.0 Y36.82",
"G1 X12.071 Y29.748",
"G1 X12.071 Y43.89",
"G1 X5.0 Y36.82",
"G1 X5.0 Y50.962",
"G1 X12.071 Y43.89",
"G1 X12.071 Y58.032",
"G1 X5.0 Y50.962",
"G1 X5.0 Y65.104",
"G1 X12.071 Y58.032",
"G1 X12.071 Y72.174",
"G1 X5.0 Y65.104",
"G1 X5.0 Y79.246",
"G1 X12.071 Y72.174",
"G1 X12.071 Y86.316",
"G1 X5.0 Y79.246",
"G1 X5.0 Y93.388",
"G1 X12.071 Y86.316",
"G1 X12.071 Y100.458",
"G1 X5.0 Y93.388",
"G1 X5.0 Y107.53",
"G1 X12.071 Y100.458",
"G1 X12.071 Y114.6",
"G1 X5.0 Y107.53",
"G1 X5.0 Y121.672",
"G1 X12.071 Y114.6",
"G1 X12.071 Y128.742",
"G1 X5.0 Y121.672",
"G1 X5.0 Y135.813",
"G1 X12.071 Y128.742",
"G1 X12.071 Y142.884",
"G1 X5.0 Y135.813",
"G1 X5.0 Y149.955",
"G1 X12.071 Y142.884",
"G1 X12.071 Y157.026",
"G1 X5.0 Y149.955",
"G1 X5.0 Y164.097",
"G1 X12.071 Y157.026",
"G1 X12.071 Y171.168",
"G1 X5.0 Y164.097",
"G1 X5.0 Y178.24",
"G1 X12.071 Y171.168",
"G1 X12.071 Y185.31",
"G1 X5.0 Y178.24",
"G1 X5.0 Y192.382",
"G1 X12.071 Y185.31",
"G1 X12.071 Y199.452",
"G1 X5.0 Y192.382",
"G1 X5.0 Y206.524",
"G1 X12.071 Y199.452",
"G1 X12.071 Y213.594",
"G1 X5.0 Y206.524",
"G1 X5.0 Y220.666",
"G1 X12.071 Y213.594",
"G1 X12.071 Y227.736",
"G1 X5.0 Y220.666",
"G1 X5.0 Y234.808",
"G1 X12.071 Y227.736",
"G1 X12.071 Y241.878",
"G1 X5.0 Y234.808",
"G1 X5.0 Y248.95",
"G1 X12.071 Y241.878",
"G1 X12.071 Y256.02",
"G1 X5.0 Y248.95",
"G1 X5.0 Y263.092",
"G1 X12.071 Y256.02",
"G1 X12.071 Y270.162",
"G1 X5.0 Y263.092",
"G1 X5.0 Y277.234",
"G1 X12.071 Y270.162",
"G1 X12.071 Y284.304",
"G1 X5.0 Y277.234",
"G1 X5.0 Y291.376",
"G1 X12.071 Y284.304",
"G1 X12.071 Y298.446",
"G1 X5.0 Y291.376",
"G1 X5.0 Y305.518",
"G1 X12.071 Y298.446",
"G1 X12.071 Y312.588",
"G1 X5.0 Y305.518",
"G1 X5.0 Y319.66",
"G1 X12.071 Y312.588",
"G1 X12.071 Y326.73",
"G1 X5.0 Y319.66",
"G1 X5.0 Y333.802",
"G1 X12.071 Y326.73",
"G1 X8.535499999999999 Y346.4645",
"G4 P0",
"",
"G1 X177.5 Y177.5",
"M84",
"M201 X5000 Y5000",
"M204 T3000 P1000"
]}

def main():
    
    streamFromGcode({"commands": ["M920 X100"]})
    time.sleep(1)
    for i in range(2500):
    # each cycle takes ~2min. Pause between each cycle
        print(i)    
        streamFromGcode(j)
        for _ in range(42):
            time.sleep(1)
    streamFromGcode({"commands": ["M920 X125"]})
    time.sleep(5)

def streamFromGcode(j) -> None:
    post(URL_BASE + "streamFromCommands", json=j)

def post(*args, **kwargs):
    request(s.post, *args, **kwargs)
    
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
