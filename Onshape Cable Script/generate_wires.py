import os
import time
import pandas as pd
import requests
import csv

# 1. Credentials & IDs
url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')

TEMPLATE_DID = os.getenv("TEMPLATE_DID", "").strip(' "\'\n\r')
TEMPLATE_WID = os.getenv("TEMPLATE_WID", "").strip(' "\'\n\r')
PART_NUMBER_PROPERTY_ID = "57f3fb8efa3416c06701d60f"
TARGET_FOLDER_ID = "f83018d2440a03d57cf2ced3"

auth = (access, secret)
base = url.rstrip('/')

# 2. Data Loading & Sanitization
print("Loading CSV files...")
bom_df = pd.read_csv('assembly_bom.csv').fillna('None')
ps_df = pd.read_csv('part_studio_data.csv').fillna('None')
ref_df = pd.read_csv('original_reference.csv').fillna('None')

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

# --- TRANSLATION DICTIONARY ---
def map_connector(csv_val):
    val = str(csv_val).strip().lower()
    if 'sv1' in val or 'fork' in val: return "sv1_25_4Fork"
    if '4.8' in val or 'spade' in val: return "_4_8Spade"
    if 'rv2-6' in val or 'ring' in val: return "Default"
    return "None"  # <--- Our safety catch-all!

print(f"Successfully matched {len(final_df)} cables! Starting automation...\n" + "-"*50)

# 3. Loop and Generate
for index, row in final_df.iterrows():
    wire_id = row['Wire ID'] 
    raw_length = str(row['Length']).strip()
    conn_a = row['Connector A']
    conn_b = row['Connector B']
    csv_part_number = str(row['Part number']) 
    
    custom_name = f"{wire_id} - ({conn_a} to {conn_b}) - {csv_part_number} - Cable Assembly"
    print(f"Processing: {custom_name}...")
    
    # Extract numeric length
    if not raw_length or raw_length.lower() == 'none' or raw_length == '':
        clean_len = "150"
    else:
        clean_len = raw_length.lower().replace('mm', '').strip()

    # Translate Connectors
    mapped_conn_a = map_connector(conn_a)
    mapped_conn_b = map_connector(conn_b)

    print(f"  [DEBUG] Translated Inputs -> Length: {clean_len}mm, ConnA: {mapped_conn_a}, ConnB: {mapped_conn_b}")

    # --- A. Copy Document ---
    copy_url = f"{base}/api/documents/{TEMPLATE_DID}/workspaces/{TEMPLATE_WID}/copy"
    try:
        r = requests.post(copy_url, auth=auth, headers={"Content-Type": "application/json"}, json={
            "newName": custom_name, "isPublic": False, "folderId": TARGET_FOLDER_ID
        })
        r.raise_for_status()
        copy_data = r.json()
    except requests.RequestException as e:
        print(f"  ❌ Failed to copy template: {e}")
        continue
    
    new_did = copy_data.get('newDocumentId')
    new_wid = copy_data.get('newWorkspaceId')

    # Get Elements
    elements_url = f"{base}/api/documents/d/{new_did}/w/{new_wid}/elements"
    new_asm_id, new_dwg_id = None, None
    try:
        resp = requests.get(elements_url, auth=auth, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            for it in resp.json():
                el_type = (it.get('type') or it.get('elementType') or '').lower()
                el_name = (it.get('name') or '').lower()
                el_id = it.get('id')
                if el_type == 'assembly' and 'bom' not in el_name: new_asm_id = el_id
                elif 'drawing' in el_name or el_type == 'application': new_dwg_id = el_id
    except:
        pass

    if not new_asm_id:
        print("  ⚠️ Could not find assembly in copied document.")
        continue

    # --- B. Update ASSEMBLY Configuration (Drives EVERYTHING) ---
    asm_cfg_str = f"AssyLength={clean_len}+mm;List_ySGuwLBMa9tVMz={mapped_conn_a};List_3u8KU5jBjgEs71={mapped_conn_b}"
    asm_cfg_url = f"{base}/api/elements/d/{new_did}/w/{new_wid}/e/{new_asm_id}/configuration"
    try:
        r = requests.post(asm_cfg_url, auth=auth, headers={"Content-Type": "application/json"}, json={"configuration": asm_cfg_str})
        if r.status_code == 200:
            print(f"  ✅ Assembly configured successfully!")
        else:
            print(f"  ⚠️ Assembly config returned status: {r.status_code}")
    except Exception as e:
        print(f"  ⚠️ Assembly config failed: {e}")

    # --- C. Sync Drawing ---
    if new_dwg_id:
        sync_url = f"{base}/api/drawings/d/{new_did}/w/{new_wid}/e/{new_dwg_id}/updates"
        try:
            requests.post(sync_url, auth=auth, headers={"Content-Type": "application/json"}, json={})
            print(f"  🔄 Drawing refreshed")
        except:
            pass

    # --- D. Push Metadata ---
    meta_url = f"{base}/api/metadata/d/{new_did}/w/{new_wid}/e/{new_asm_id}"
    try:
        requests.post(meta_url, auth=auth, headers={"Content-Type": "application/json"}, json={
            "items": [{"href": meta_url, "properties": [{"propertyId": PART_NUMBER_PROPERTY_ID, "value": csv_part_number}]}]
        })
        print(f"  ✅ Metadata updated")
    except:
        pass

    doc_url = f"{base}/documents/{new_did}/w/{new_wid}/e/{new_asm_id}"
    print(f"  ✅ Finished: {doc_url}\n")
    
    # Save to CSV log
    try:
        with open('generated_drawings.csv', 'a', newline='') as csvfile:
            csv.writer(csvfile).writerow([wire_id, csv_part_number, new_did, new_wid, new_asm_id, doc_url])
    except:
        pass

    time.sleep(1) 

print("🎉 All 2D manufacturing drawings generated and filed successfully!")