import os
import time
import pandas as pd
import requests
import csv
import json
from datetime import datetime

# ==========================================
# 1. GLOBAL LOGGING ENGINE
# ==========================================
LOG_FILE = "ONSHAPE_EXECUTION_LOG.txt"

def write_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    print(log_entry.strip())  
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def log_api_call(method, url, payload, response):
    if response and response.status_code >= 400:
        write_log(f"--- API ERROR ({response.status_code}) ---")
        write_log(f"URL: {url}")
        try:
            write_log(f"BODY: {json.dumps(response.json(), indent=2)}\n")
        except:
            write_log(f"BODY: {response.text}\n")

def api_request(method, url, auth, headers=None, json_payload=None):
    try:
        if method.upper() == 'GET':
            r = requests.get(url, auth=auth, headers=headers)
        elif method.upper() == 'POST':
            r = requests.post(url, auth=auth, headers=headers, json=json_payload)
        else:
            raise ValueError(f"Unsupported method: {method}")
        log_api_call(method, url, json_payload, r)
        return r
    except Exception as e:
        write_log(f"!!! FATAL NETWORK ERROR !!!\n{e}\n")
        return None

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== ONSHAPE AUTOMATION LOG INITIALIZED AT {datetime.now()} ===\n\n")

# ==========================================
# 2. CREDENTIALS & IDs
# ==========================================
write_log("Loading credentials from environment...")
url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')

TEMPLATE_DID = os.getenv("TEMPLATE_DID", "").strip(' "\'\n\r')
TEMPLATE_WID = os.getenv("TEMPLATE_WID", "").strip(' "\'\n\r')

# ONSHAPE CORE METADATA PROPERTY IDs
PART_NUMBER_PROPERTY_ID = "57f3fb8efa3416c06701d60f"
NAME_PROPERTY_ID = "57f3fb8efa3416c06701d60d" # Explicitly targets the Element Name field
TARGET_FOLDER_ID = "f83018d2440a03d57cf2ced3"

auth = (access, secret)
base = url.rstrip('/')

# ==========================================
# 3. DATA LOADING & DB SANITIZATION
# ==========================================
try:
    bom_df = pd.read_csv('assembly_bom.csv').fillna('None')
    ps_df = pd.read_csv('part_studio_data.csv').fillna('None')
    ref_df = pd.read_csv('original_reference.csv').fillna('None')
except Exception as e:
    write_log(f"CRITICAL ERROR: Could not load CSV files. {e}")
    exit()

for df in [bom_df, ps_df, ref_df]:
    df.columns = df.columns.str.strip()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

ref_df['Connector A'] = ref_df['Connector A'].replace(['nan', 'None', ''], 'None')
ref_df['Connector B'] = ref_df['Connector B'].replace(['nan', 'None', ''], 'None')

merge_1 = pd.merge(ps_df, bom_df, left_on='ID', right_on='Name', how='inner')
final_df = pd.merge(merge_1, ref_df, left_on='ID', right_on='Wire ID', how='inner')

# EXACT 24-PART TRANSLATION DICTIONARY
def map_connector(csv_val):
    val = str(csv_val).strip().lower()
    
    # 1. MOLEX Series
    if '0430200211' in val: return "_0430200211_Molex"
    if '0430200400' in val: return "_0430200400_Molex"
    if '0430250208' in val: return "_0430250208_Molex"
    if '0430250400' in val: return "_0430250400_Molex"
    if '0436450308' in val: return "Molex_0436450308"
    if '436400308' in val: return "Molex_436400308"
    
    # 2. XH Series (Accounts for XH2.54 2P, XH2.54 4P, and PHR2.0-6P)
    if 'xh2.54 4p' in val or 'xhp-4' in val or 'xhp 4' in val: return "XHP_4"
    if 'xh2.54 2p' in val or 'xhp-2' in val or 'xhp 2' in val: return "XHP_2"
    if 'phr2.0-6p' in val or 'xhp-6' in val or 'xhp 6' in val: return "XHP_6"
    if 'xha-4' in val or 'xha 4' in val or 'xha4' in val: return "XHA_4"
    
    # 3. JST PHR
    if 'phr-3' in val or 'phr 3' in val: return "JST_PHR_3"
    if 'phr-2' in val or 'phr 2' in val and 'phr2.0' not in val: return "PHR_2"
    
    # 4. USB & HDMI
    if 'usb' in val:
        if 'c' in val: return "USB_C_Male"
        if 'female' in val: return "USBA_Female"
        return "USB_A_Male"
    if 'hdmi' in val:
        if 'micro' in val: return "MicroHDMI"
        return "HDMI"
        
    # 5. A1001H & RJ45
    if 'a1001h' in val: return "A1001H_05P_1"
    if 'rj45' in val: return "RJ45Male"

    # 6. Spade Connectors
    if 'spade' in val:
        if '6' in val: return "_6Spade" # Matches 6.3Spade
        return "_4_8Spade"
    
    # 7. KST Series (E1008, E2510, E7508)
    if 'kst' in val or '1008' in val or '2510' in val or '7508' in val:
        if '2510' in val: return "KST_E2510"
        if '7508' in val: return "KST_E7508"
        return "KST_E1008" 
        
    # 8. Fork Connectors (SV1 vs SV2)
    if 'fork' in val or 'sv1' in val or 'sv2' in val:
        if 'sv2' in val: return "SV2_4Fork"
        return "sv1_25_4Fork" 
        
    # 9. Ring Connectors
    if 'ring' in val or 'rv2' in val: return "Default"
    
    # 10. Blank/Catch-All
    return "None"

# ==========================================
# 4. CORE EXECUTION LOOP
# ==========================================
for index, row in final_df.iterrows():
    wire_id = row['Wire ID'] 
    raw_length = str(row['Length']).strip()
    conn_a = row['Connector A']
    conn_b = row['Connector B']
    
    # Safely extract Part Number and Cable Description
    csv_part_number = str(row.get('Part number', row.get('Onshape Part Number', ''))).strip()
    csv_cable_desc = str(row.get('Cable Description', 'Cable Assembly')).strip()
    
    # Fallback if the Cable Description column is accidentally left blank
    if csv_cable_desc.lower() in ['nan', 'none', '']:
        csv_cable_desc = 'Cable Assembly'
    
    # Generate the Document File Name
    custom_name = f"{wire_id} - {csv_cable_desc} - ({conn_a} to {conn_b}) - {csv_part_number}"
    write_log(f"\n{'='*80}\nPROCESSING WIRE: {wire_id}\n{'='*80}")
    
    if not raw_length or raw_length.lower() == 'none' or raw_length == '':
        clean_len = 150.0
    else:
        clean_len = float(raw_length.lower().replace('mm', '').strip())

    mapped_conn_a = map_connector(conn_a)
    mapped_conn_b = map_connector(conn_b)

    # --- A. Copy Document ---
    write_log(">> STEP 1: Copying Master Template...")
    copy_url = f"{base}/api/documents/{TEMPLATE_DID}/workspaces/{TEMPLATE_WID}/copy"
    r_copy = api_request('POST', copy_url, auth, headers={"Content-Type": "application/json"}, json_payload={"newName": custom_name, "isPublic": False, "folderId": TARGET_FOLDER_ID})
    
    if not r_copy or r_copy.status_code != 200:
        write_log(f"ABORTING {wire_id}: Failed to copy.")
        continue
        
    new_did = r_copy.json().get('newDocumentId')
    new_wid = r_copy.json().get('newWorkspaceId')

    # --- B. Get Element IDs ---
    write_log(">> STEP 2: Locating Elements...")
    elements_url = f"{base}/api/documents/d/{new_did}/w/{new_wid}/elements"
    r_elems = api_request('GET', elements_url, auth, headers={"Accept": "application/json"})
    
    new_asm_id, new_ps_id, new_dwg_id = None, None, None
    if r_elems and r_elems.status_code == 200:
        for it in r_elems.json():
            el_type = (it.get('type') or '').lower()
            el_name = (it.get('name') or '').lower()
            if el_type == 'assembly' and 'bom' not in el_name: new_asm_id = it.get('id')
            elif el_type == 'part studio': new_ps_id = it.get('id')
            elif 'drawing' in el_name or el_type == 'application': new_dwg_id = it.get('id')

    if not new_asm_id or not new_ps_id:
        continue

    # --- C. Update ASSEMBLY Schema Defaults ---
    write_log(">> STEP 3: Patching Assembly Default Configuration Parameters...")
    asm_cfg_url = f"{base}/api/elements/d/{new_did}/w/{new_wid}/e/{new_asm_id}/configuration"
    r_asm_schema = api_request('GET', asm_cfg_url, auth, headers={"Accept": "application/json"})
    if r_asm_schema and r_asm_schema.status_code == 200:
        cfg_data = r_asm_schema.json()
        for param in cfg_data.get('configurationParameters', []):
            p_id = param.get('message', {}).get('parameterId')
            if p_id == 'AssyLength':
                param['message']['rangeAndDefault']['message']['defaultValue'] = float(clean_len)
            elif p_id == 'List_ySGuwLBMa9tVMz':
                param['message']['defaultValue'] = mapped_conn_a
            elif p_id == 'List_3u8KU5jBjgEs71':
                param['message']['defaultValue'] = mapped_conn_b
        cfg_data['currentConfiguration'] = [] 
        api_request('POST', asm_cfg_url, auth, headers={"Content-Type": "application/json"}, json_payload=cfg_data)

    # --- D. Update PART STUDIO Schema Defaults ---
    write_log(">> STEP 4: Patching Part Studio Default Configuration Parameters...")
    ps_cfg_url = f"{base}/api/elements/d/{new_did}/w/{new_wid}/e/{new_ps_id}/configuration"
    r_ps_schema = api_request('GET', ps_cfg_url, auth, headers={"Accept": "application/json"})
    if r_ps_schema and r_ps_schema.status_code == 200:
        ps_cfg_data = r_ps_schema.json()
        for param in ps_cfg_data.get('configurationParameters', []):
            p_id = param.get('message', {}).get('parameterId')
            if p_id == 'WireLength':
                param['message']['rangeAndDefault']['message']['defaultValue'] = float(clean_len)
        ps_cfg_data['currentConfiguration'] = []
        api_request('POST', ps_cfg_url, auth, headers={"Content-Type": "application/json"}, json_payload=ps_cfg_data)

    # --- E. PROGRAMMATIC DRAWING VIEW REFERENCE OVERWRITE ---
    if new_dwg_id:
        write_log(">> STEP 5: Re-linking Drawing Views Locally...")
        drawing_modify_url = f"{base}/api/drawings/d/{new_did}/w/{new_wid}/e/{new_dwg_id}/modify"
        drawing_payload = {
            "viewModifications": [
                {
                    "btType": "BTDrawingViewModification-150",
                    "viewReference": {
                        "btType": "BTElementReference-120",
                        "documentId": new_did,
                        "workspaceId": new_wid,
                        "elementId": new_asm_id 
                    }
                }
            ]
        }
        api_request('POST', drawing_modify_url, auth, headers={"Content-Type": "application/json"}, json_payload=drawing_payload)

    # --- F. Write Properties Metadata (Name & Part Number) ---
    write_log(">> STEP 6: Natively Renaming Tabs & Pushing Metadata...")
    
    # Push the exact Cable Description as the official Name of the Assembly Tab
    asm_meta_url = f"{base}/api/metadata/d/{new_did}/w/{new_wid}/e/{new_asm_id}"
    api_request('POST', asm_meta_url, auth, headers={"Content-Type": "application/json"}, json_payload={
        "items": [{"href": asm_meta_url, "properties": [
            {"propertyId": PART_NUMBER_PROPERTY_ID, "value": csv_part_number},
            {"propertyId": NAME_PROPERTY_ID, "value": csv_cable_desc}
        ]}]
    })
    
    # Push the exact Cable Description as the official Name of the 2D Drawing Tab
    if new_dwg_id:
        dwg_meta_url = f"{base}/api/metadata/d/{new_did}/w/{new_wid}/e/{new_dwg_id}"
        api_request('POST', dwg_meta_url, auth, headers={"Content-Type": "application/json"}, json_payload={
            "items": [{"href": dwg_meta_url, "properties": [
                {"propertyId": PART_NUMBER_PROPERTY_ID, "value": csv_part_number},
                {"propertyId": NAME_PROPERTY_ID, "value": csv_cable_desc}
            ]}]
        })
    
    # --- G. Build Direct Parameterized View URL ---
    config_url_string = f"AssyLength={clean_len}+mm;List_ySGuwLBMa9tVMz={mapped_conn_a};List_3u8KU5jBjgEs71={mapped_conn_b}"
    encoded_config = config_url_string.replace("=", "%3D").replace(";", "%3B")
    
    doc_url = f"{base}/documents/{new_did}/w/{new_wid}/e/{new_asm_id}?configuration={encoded_config}"
    write_log(f"\n>> FINAL LINK: {doc_url}")
    
    try:
        with open('generated_drawings.csv', 'a', newline='') as csvfile:
            csv.writer(csvfile).writerow([wire_id, csv_part_number, new_did, new_wid, new_asm_id, doc_url])
    except:
        pass

    time.sleep(1) 

write_log("\n=== ALL PROCESSES FINISHED PERFECTLY ===")