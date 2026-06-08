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
PART_NUMBER_PROPERTY_ID = "57f3fb8efa3416c06701d60f"
TARGET_FOLDER_ID = "f83018d2440a03d57cf2ced3"

auth = (access, secret)
base = url.rstrip('/')

# ==========================================
# 3. DATA LOADING
# ==========================================
try:
    bom_df = pd.read_csv('assembly_bom.csv').fillna('None')
    ps_df = pd.read_csv('part_studio_data.csv').fillna('None')
    ref_df = pd.read_csv('original_reference.csv').fillna('None')
except Exception as e:
    write_log(f"CRITICAL ERROR: Could not load CSV files. {e}")
    exit()

bom_df.columns = bom_df.columns.str.strip()
ps_df.columns = ps_df.columns.str.strip()
ref_df.columns = ref_df.columns.str.strip()

for df in [bom_df, ps_df, ref_df]:
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

ref_df['Connector A'] = ref_df['Connector A'].replace(['nan', 'None', ''], 'None')
ref_df['Connector B'] = ref_df['Connector B'].replace(['nan', 'None', ''], 'None')

merge_1 = pd.merge(ps_df, bom_df, left_on='ID', right_on='Name', how='inner')
final_df = pd.merge(merge_1, ref_df, left_on='ID', right_on='Wire ID', how='inner')

# EXACT TRANSLATION DICTIONARY
def map_connector(csv_val):
    val = str(csv_val).strip().lower()
    if 'sv1' in val or 'fork' in val: return "sv1_25_4Fork"
    if '4.8' in val or 'spade' in val: return "_4_8Spade"
    if 'rv2-6' in val or 'ring' in val: return "Default"
    return "None"

# ==========================================
# 4. CORE EXECUTION LOOP
# ==========================================
for index, row in final_df.iterrows():
    wire_id = row['Wire ID'] 
    raw_length = str(row['Length']).strip()
    conn_a = row['Connector A']
    conn_b = row['Connector B']
    csv_part_number = str(row['Part number']) 
    
    custom_name = f"{wire_id} - ({conn_a} to {conn_b}) - {csv_part_number} - Cable Assembly"
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
        write_log(f"ABORTING {wire_id}: Missing Assembly or Part Studio.")
        continue

    # --- C. Update ASSEMBLY Schema Defaults ---
    write_log(">> STEP 3: Patching Assembly Default Configuration...")
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
    write_log(">> STEP 4: Patching Part Studio Default Configuration...")
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

    # --- E. Write Metadata ---
    write_log(">> STEP 5: Writing Metadata...")
    meta_url = f"{base}/api/metadata/d/{new_did}/w/{new_wid}/e/{new_asm_id}"
    api_request('POST', meta_url, auth, headers={"Content-Type": "application/json"}, json_payload={"items": [{"href": meta_url, "properties": [{"propertyId": PART_NUMBER_PROPERTY_ID, "value": csv_part_number}]}]})
    
    # --- F. BUILD DIRECT PARAMETERIZED LINK ---
    # 🛠️ This forces the browser to explicitly demand the correct shape upon opening, skipping the cached fallback mesh!
    config_url_string = f"AssyLength={clean_len}+mm;List_ySGuwLBMa9tVMz={mapped_conn_a};List_3u8KU5jBjgEs71={mapped_conn_b}"
    encoded_config = config_url_string.replace("=", "%3D").replace(";", "%3B")
    
    doc_url = f"{base}/documents/{new_did}/w/{new_wid}/e/{new_asm_id}?configuration={encoded_config}"
    write_log(f"\n>> FINAL HIGH-FIDELITY LINK: {doc_url}")
    
    try:
        with open('generated_drawings.csv', 'a', newline='') as csvfile:
            csv.writer(csvfile).writerow([wire_id, csv_part_number, new_did, new_wid, new_asm_id, doc_url])
    except:
        pass

    time.sleep(1) 

write_log("\n=== ALL PROCESSES FINISHED ===")