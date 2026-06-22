import os
import json
import requests

def main():
    url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
    access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
    secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')
    did = os.getenv("TEMPLATE_DID", "").strip(' "\'\n\r')
    wid = os.getenv("TEMPLATE_WID", "").strip(' "\'\n\r')
    
    auth = (access, secret)
    base = url.rstrip('/')

    print(f"🔍 Inspecting Master Template Configuration Lists...")

    # Find Assembly Tab
    r_elems = requests.get(f"{base}/api/documents/d/{did}/w/{wid}/elements", auth=auth, headers={"Accept": "application/json"})
    if r_elems.status_code != 200:
        print(f"❌ Connection failed: Status {r_elems.status_code}")
        return

    asm_id = None
    for el in r_elems.json():
        el_type = (el.get('type') or el.get('elementType') or '').lower()
        el_name = (el.get('name') or '').lower()
        if el_type == 'assembly' and 'bom' not in el_name:
            asm_id = el.get('id')
            break

    if not asm_id:
        print("❌ Could not find Assembly tab.")
        return

    # Grab Configuration Matrix Data
    r_cfg = requests.get(f"{base}/api/elements/d/{did}/w/{wid}/e/{asm_id}/configuration", auth=auth, headers={"Accept": "application/json"})
    if r_cfg.status_code != 200:
        print(f"❌ Failed to fetch parameters: Status {r_cfg.status_code}")
        return

    cfg_data = r_cfg.json()
    
    print("\n========================================================")
    print("📋 DUMPING SEPARATE MAPS FOR COMNNECTOR A & B")
    print("========================================================")

    for param in cfg_data.get('configurationParameters', []):
        message = param.get('message', {})
        param_name = message.get('parameterName') # "Connector A" or "Connector B"
        
        if param_name in ["Connector A", "Connector B"]:
            print(f"\n🔹 EXTRACTING ID MAP FOR: {param_name.upper()}")
            print("----------------------------------------")
            options = message.get('options', [])
            for opt in options:
                opt_msg = opt.get('message', {})
                ui_name = opt_msg.get('optionName')  # What you see in Excel/Onshape UI
                api_id = opt_msg.get('option')      # The secret background ID
                print(f"   Excel label: '{ui_name}' ---> Maps to API ID: '{api_id}'")

if __name__ == "__main__":
    main()