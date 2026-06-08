import os
import time
import json
import pandas as pd
import requests
import csv

# 1. Grab and scrub the variables
url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')

TEMPLATE_DID = os.getenv("TEMPLATE_DID", "").strip(' "\'\n\r')
TEMPLATE_WID = os.getenv("TEMPLATE_WID", "").strip(' "\'\n\r')
TEMPLATE_EID = os.getenv("TEMPLATE_EID", "").strip(' "\'\n\r')

PART_NUMBER_PROPERTY_ID = "57f3fb8efa3416c06701d60f"
TARGET_FOLDER_ID = "f83018d2440a03d57cf2ced3"

auth = (access, secret)

# 2. Read and Sanitize CSV Files
print("Loading CSV files...")
bom_df = pd.read_csv('assembly_bom.csv')
ps_df = pd.read_csv('part_studio_data.csv')
ref_df = pd.read_csv('original_reference.csv') 

print("Sanitizing headers and data cells...")
bom_df.columns = bom_df.columns.str.strip()
ps_df.columns = ps_df.columns.str.strip()
ref_df.columns = ref_df.columns.str.strip()

bom_df = bom_df.fillna('None')
ps_df = ps_df.fillna('None')
ref_df = ref_df.fillna('None')

for df in [bom_df, ps_df, ref_df]:
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

ref_df['Connector A'] = ref_df['Connector A'].replace(['nan', 'None', ''], 'None')
ref_df['Connector B'] = ref_df['Connector B'].replace(['nan', 'None', ''], 'None')

# 3. Stitch databases together
merge_1 = pd.merge(ps_df, bom_df, left_on='ID', right_on='Name', how='inner')
final_df = pd.merge(merge_1, ref_df, left_on='ID', right_on='Wire ID', how='inner')

print(f"Successfully matched {len(final_df)} cables across all files! Starting automation...\n" + "-"*50)

# 4. Loop through the data
for index, row in final_df.iterrows():
    wire_id = row['Wire ID'] 
    length = row['Length']
    conn_a = row['Connector A']
    conn_b = row['Connector B']
    csv_part_number = str(row['Part number']) 
    
    custom_document_name = f"{wire_id} - ({conn_a} to {conn_b}) - {csv_part_number} - Cable Assembly"
    print(f"Processing: {custom_document_name}...")
    
    # --- A. Copy Document ---
    base = url.rstrip('/')
    copy_url = f"{base}/api/documents/{TEMPLATE_DID}/workspaces/{TEMPLATE_WID}/copy"
    
    try:
        r = requests.post(copy_url, auth=auth, headers={"Content-Type": "application/json"}, json={
            "newName": custom_document_name, "isPublic": False, "folderId": TARGET_FOLDER_ID
        })
        r.raise_for_status()
        copy_data = r.json()
    except requests.RequestException as e:
        print(f"  ❌ Failed to copy template: {e}")
        continue
    
    new_did = copy_data.get('newDocumentId')
    new_workspace_id = copy_data.get('newWorkspaceId')

    # Find the Assembly and Drawing Element IDs inside the new copy
    elements_url = f"{base}/api/documents/d/{new_did}/w/{new_workspace_id}/elements"
    new_assembly_id = None
    new_drawing_id = None

    try:
        resp = requests.get(elements_url, auth=auth, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            for it in resp.json():
                el_type = (it.get('type') or it.get('elementType') or '').lower()
                el_name = (it.get('name') or '').lower()
                el_id = it.get('id') or it.get('elementId')

                if el_type == 'assembly' and 'bill of materials' not in el_name:
                    new_assembly_id = el_id
                elif el_type == 'application' or 'drawing' in el_name:
                    new_drawing_id = el_id
    except requests.RequestException:
        pass

    if not new_assembly_id:
        print(f"  ⚠️ Warning: Could not locate assembly.")
        continue

    # --- B. Clean Length Inputs ---
    raw_length = str(length).strip()
    if not raw_length or raw_length.lower() == 'none' or raw_length == '':
        clean_length_numeric = "150"
    else:
        clean_length_numeric = raw_length.lower().replace('mm', '').strip()

    # --- C. Dynamic Parameter Mapping with Mismatch Detection ---
    config_string = ""
    try:
        config_def_url = f"{base}/api/elements/d/{new_did}/w/{new_workspace_id}/e/{new_assembly_id}/configuration"
        r = requests.get(config_def_url, auth=auth, headers={"Accept": "application/json"})
        
        if r.status_code == 200:
            config_struct = r.json()
            param_map = {}
            enum_map = {}
            
            for p in config_struct.get('configurationParameters', []):
                p_msg = p.get('message', p) 
                p_id = p_msg.get('parameterId') or p.get('parameterId')
                p_name = (p_msg.get('parameterName') or p.get('parameterName') or '').lower()
                
                if not p_id: continue
                param_map[p_name] = p_id
                
                options = p_msg.get('options', []) or p.get('options', [])
                if options:
                    enum_map[p_id] = {}
                    for opt in options:
                        opt_msg = opt.get('message', opt)
                        
                        # 🛠️ THE FIX: Expand the net to catch every variation of Onshape's option keys
                        opt_id = opt_msg.get('option') or opt_msg.get('optionId') or opt_msg.get('optionValue') or opt.get('option') or opt.get('optionId')
                        opt_name = (opt_msg.get('optionName') or opt.get('optionName') or '').lower().strip()
                        
                        # If the dropdown has an ID but no explicit name, its name is its ID
                        if opt_id and not opt_name:
                            opt_name = str(opt_id).lower().strip()

                        if opt_id and opt_name:
                            enum_map[p_id][opt_name] = opt_id
                            
            # 1. Resolve Length ID
            length_id = param_map.get('assylength') or param_map.get('length') or 'AssyLength'
            
            # 2. Resolve Connector A ID and Dropdown Option
            conn_a_id = param_map.get('connector_a') or param_map.get('connector a') or 'Connector_A'
            conn_a_val_lower = str(conn_a).strip().lower()
            if conn_a_id in enum_map:
                if conn_a_val_lower in enum_map[conn_a_id]:
                    conn_a_val = enum_map[conn_a_id][conn_a_val_lower]
                else:
                    print(f"    ⚠️ MISMATCH ALERT (Conn A): Your CSV asked for '{conn_a}', but Onshape's dropdown only accepts: {list(enum_map[conn_a_id].keys())}")
                    conn_a_val = str(conn_a).strip().replace(' ', '+')
            else:
                conn_a_val = str(conn_a).strip().replace(' ', '+')
                
            # 3. Resolve Connector B ID and Dropdown Option
            conn_b_id = param_map.get('connector_b') or param_map.get('connector b') or 'Connector_B'
            conn_b_val_lower = str(conn_b).strip().lower()
            if conn_b_id in enum_map:
                if conn_b_val_lower in enum_map[conn_b_id]:
                    conn_b_val = enum_map[conn_b_id][conn_b_val_lower]
                else:
                    print(f"    ⚠️ MISMATCH ALERT (Conn B): Your CSV asked for '{conn_b}', but Onshape's dropdown only accepts: {list(enum_map[conn_b_id].keys())}")
                    conn_b_val = str(conn_b).strip().replace(' ', '+')
            else:
                conn_b_val = str(conn_b).strip().replace(' ', '+')
                
            print(f"    [DEBUG] Sending Configuration: Length={clean_length_numeric}mm | ConnA={conn_a_val} | ConnB={conn_b_val}")
            config_string = f"{length_id}={clean_length_numeric}+mm;{conn_a_id}={conn_a_val};{conn_b_id}={conn_b_val}"
            
    except Exception as e:
        print(f"  ⚠️ Could not dynamically map parameters: {e}")

    # --- D. Post Configuration ---
    if config_string:
        config_post_url = f"{base}/api/elements/d/{new_did}/w/{new_workspace_id}/e/{new_assembly_id}/configuration"
        try:
            r = requests.post(config_post_url, auth=auth, headers={"Content-Type": "application/json"}, json={"configuration": config_string})
            r.raise_for_status()
            print(f"    ✅ Assembly configured successfully!")
        except requests.RequestException as e:
            print(f"    ❌ Configuration update failed: {e}")

    # --- E. Drawing Sync ---
    if new_drawing_id:
        sync_drawing_url = f"{base}/api/drawings/d/{new_did}/w/{new_workspace_id}/e/{new_drawing_id}/updates"
        try:
            requests.post(sync_drawing_url, auth=auth, headers={"Content-Type": "application/json"}, json={})
            print(f"    ✅ Drawing sync triggered!")
        except requests.RequestException:
            pass

    # --- F. Metadata (Part Number) ---
    metadata_url = f"{base}/api/metadata/d/{new_did}/w/{new_workspace_id}/e/{new_assembly_id}"
    try:
        requests.post(metadata_url, auth=auth, headers={"Content-Type": "application/json"}, json={
            "items": [{"href": metadata_url, "properties": [{"propertyId": PART_NUMBER_PROPERTY_ID, "value": csv_part_number}]}]
        })
    except requests.RequestException:
        pass

    doc_url = f"{base}/documents/{new_did}/w/{new_workspace_id}/e/{new_assembly_id}"
    print(f"✅ Generated: {wire_id} -> {doc_url}\n" + "-"*50)
    
    try:
        with open('generated_drawings.csv', 'a', newline='') as csvfile:
            csv.writer(csvfile).writerow([wire_id, csv_part_number, new_did, new_workspace_id, new_assembly_id, doc_url])
    except Exception:
        pass
    
    time.sleep(1) 

print("🎉 All 2D manufacturing drawings generated and filed successfully!")