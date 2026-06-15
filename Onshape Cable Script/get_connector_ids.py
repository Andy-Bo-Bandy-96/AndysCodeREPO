import os
import json
import requests

def main():
    # 1. Grab credentials
    url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
    access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
    secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')
    did = os.getenv("TEMPLATE_DID", "").strip(' "\'\n\r')
    wid = os.getenv("TEMPLATE_WID", "").strip(' "\'\n\r')
    
    auth = (access, secret)
    base = url.rstrip('/')

    print(f"🔍 Connecting to Master Template...\n   Document: {did}\n   Workspace: {wid}")

    # 2. Get Elements to find the Assembly
    r_elems = requests.get(f"{base}/api/documents/d/{did}/w/{wid}/elements", auth=auth, headers={"Accept": "application/json"})
    if r_elems.status_code != 200:
        print(f"❌ Failed to authenticate or find document. Status: {r_elems.status_code}")
        return

    asm_id = None
    for el in r_elems.json():
        el_type = (el.get('type') or el.get('elementType') or '').lower()
        el_name = (el.get('name') or '').lower()
        if el_type == 'assembly' and 'bom' not in el_name and 'bill' not in el_name:
            asm_id = el.get('id')
            break

    if not asm_id:
        print("❌ Could not find the Assembly tab in the template.")
        return

    print(f"✅ Found Master Assembly ID: {asm_id}")
    print("🔍 Fetching Configuration Schema...")

    # 3. Get Configuration Schema
    r_cfg = requests.get(f"{base}/api/elements/d/{did}/w/{wid}/e/{asm_id}/configuration", auth=auth, headers={"Accept": "application/json"})
    if r_cfg.status_code != 200:
        print(f"❌ Failed to get configuration. Status: {r_cfg.status_code}")
        return

    cfg_data = r_cfg.json()

    # 4. Save the exact parameters block to a file
    with open('template_connectors_dump.txt', 'w', encoding='utf-8') as f:
        # We only need the parameters array, which contains the dropdown Enums
        f.write(json.dumps(cfg_data.get('configurationParameters', []), indent=2))

    print("\n✅ Success! Connector schema extracted and saved to 'template_connectors_dump.txt'.")
    print("Please open that text file, copy all the text, and paste it into your next message.")

if __name__ == "__main__":
    main()