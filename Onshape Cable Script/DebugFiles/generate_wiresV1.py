import os
import time
import json
import pandas as pd
import requests
import csv

# 1. Grab and scrub the variables 1Password injected
url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')

TEMPLATE_DID = os.getenv("TEMPLATE_DID", "").strip(' "\'\n\r')
TEMPLATE_WID = os.getenv("TEMPLATE_WID", "").strip(' "\'\n\r')
TEMPLATE_EID = os.getenv("TEMPLATE_EID", "").strip(' "\'\n\r')

# 2. Hardcoded Onshape database IDs
PART_NUMBER_PROPERTY_ID = "57f3fb8efa3416c06701d60f"
TARGET_FOLDER_ID = "f83018d2440a03d57cf2ced3"

# 3. Securely initialize the Onshape Client mapping
# Use HTTP Basic Auth with `requests` for reliable direct API calls
auth = (access, secret)

# 4. Read all THREE CSV Files
print("Loading CSV files...")
bom_df = pd.read_csv('assembly_bom.csv')
ps_df = pd.read_csv('part_studio_data.csv')
ref_df = pd.read_csv('original_reference.csv') 

# 🛠️ DATA SANITIZATION ROUTINE
print("Sanitizing headers and data cells...")
bom_df.columns = bom_df.columns.str.strip()
ps_df.columns = ps_df.columns.str.strip()
ref_df.columns = ref_df.columns.str.strip()

# Strip hidden spaces from the actual text fields inside the files
for df in [bom_df, ps_df, ref_df]:
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

# Gracefully replace missing or blank connector fields with 'None' string
ref_df['Connector A'] = ref_df['Connector A'].replace(['nan', ''], 'None')
ref_df['Connector B'] = ref_df['Connector B'].replace(['nan', ''], 'None')

# 5. The 3-Way Merge Magic
print("Stitching databases together...")

# Merge 1: Combine Part Studio Data ('ID') and BOM Data ('Name')
merge_1 = pd.merge(ps_df, bom_df, left_on='ID', right_on='Name', how='inner')

# Merge 2: Combine that result with the Original Reference sheet
final_df = pd.merge(merge_1, ref_df, left_on='ID', right_on='Wire ID', how='inner')

print(f"Successfully matched {len(final_df)} cables across all files! Starting automation...")
print("-" * 50)

# 6. Loop through the fully merged and sanitized data
for index, row in final_df.iterrows():
    wire_id = row['Wire ID'] 
    length = row['Length']
    conn_a = row['Connector A']
    conn_b = row['Connector B']
    csv_part_number = str(row['Part number']) 
    
    # Custom Naming Convention
    custom_document_name = f"{wire_id} - ({conn_a} to {conn_b}) - {csv_part_number} - Cable Assembly"
    
    print(f"Processing: {custom_document_name}...")
    
    # --- A. Copy the Master Template Directly Into the Target Folder ---
    copy_payload = {
        "newName": custom_document_name,
        "isPublic": False,
        "folderId": TARGET_FOLDER_ID
    }
    
    # 🛠️ RESTORED ENDPOINT syntax back to /w/ for document copy mapping
    # Build absolute URL and perform POST using `requests` with Basic Auth
    base = url.rstrip('/')
    copy_url = f"{base}/api/documents/{TEMPLATE_DID}/workspaces/{TEMPLATE_WID}/copy"

    try:
        r = requests.post(copy_url, auth=auth, headers={"Content-Type": "application/json"}, json=copy_payload)
        r.raise_for_status()
        copy_data = r.json()
    except requests.RequestException as e:
        print(f"Failed to copy template for {wire_id}: {e}")
        print(f"Response: {getattr(e, 'response', None)}")
        continue
    
    new_did = copy_data.get('newDocumentId')
    new_workspace_id = copy_data.get('newWorkspaceId')
    # Determine the element ID inside the new workspace (the copied assembly's element)
    new_element_id = None

    if not new_did or not new_workspace_id:
        print(f"Copy response missing IDs for {wire_id}: {copy_data}")
        continue

    # Try common endpoints to list elements in the workspace
    element_list_endpoints = [
        f"{base}/api/documents/d/{new_did}/w/{new_workspace_id}/elements",
        f"{base}/api/documents/{new_did}/w/{new_workspace_id}/elements",
        f"{base}/api/documents/{new_did}/workspaces/{new_workspace_id}/elements",
    ]

    elements_data = None
    for ep in element_list_endpoints:
        try:
            resp = requests.get(ep, auth=auth, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                elements_data = resp.json()
                break
        except requests.RequestException:
            continue

    if not elements_data:
        print(f"Could not list elements for {wire_id} at {new_did}/{new_workspace_id}")
        continue

    # `elements_data` usually contains an 'items' list; pick the assembly-like element if possible
    items = elements_data.get('items') if isinstance(elements_data, dict) else None
    if not items:
        # Fallback: if response is a list or has other shape, try to coerce
        if isinstance(elements_data, list):
            items = elements_data
        else:
            print(f"Unexpected elements response shape for {wire_id}: {elements_data}")
            continue

    # Heuristics: prefer items with 'type' indicating assembly, or with 'name' containing 'Assembly'
    for it in items:
        t = (it.get('type') or '').lower() if isinstance(it, dict) else ''
        name = (it.get('name') or '').lower() if isinstance(it, dict) else ''
        eid = it.get('elementId') or it.get('id') or it.get('elementIdString') if isinstance(it, dict) else None
        if not eid:
            # try to find any id-like key
            for k in ['elementId', 'id', 'elementIdString']:
                if isinstance(it, dict) and k in it:
                    eid = it[k]
                    break
        if not eid:
            continue
        if 'assembly' in t or 'assembly' in name or 'asm' in t:
            new_element_id = eid
            break

    # If not found, just take the first item's id
    if not new_element_id and items:
        first = items[0]
        new_element_id = first.get('elementId') or first.get('id') if isinstance(first, dict) else None

    if not new_element_id:
        print(f"Unable to determine elementId for {wire_id}; elements: {items}")
        continue
    
    # --- B. Update the Document Variable Configuration ---
    config_string = f"AssyLength={length}+mm;Connector_A={conn_a};Connector_B={conn_b}"
    
    config_url = f"{base}/api/elements/d/{new_did}/w/{new_workspace_id}/e/{new_element_id}/configuration"

    try:
        r = requests.post(config_url, auth=auth, headers={"Content-Type": "application/json"}, json={"configuration": config_string})
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to update configuration for {wire_id}: {e}")
        continue
    
    # --- C. Push the Part Number into the Assembly Metadata Properties ---
    assembly_href = f"{url}/api/metadata/d/{new_did}/w/{new_workspace_id}/e/{new_element_id}"
    
    metadata_payload = {
        "items": [
            {
                "href": assembly_href,
                "properties": [
                    {
                        "propertyId": PART_NUMBER_PROPERTY_ID,
                        "value": csv_part_number
                    }
                ]
            }
        ]
    }
    
    metadata_url = f"{base}/api/metadata/d/{new_did}/w/{new_workspace_id}/e/{new_element_id}"

    try:
        r = requests.post(metadata_url, auth=auth, headers={"Content-Type": "application/json"}, json=metadata_payload)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to push metadata for {wire_id}: {e}")
        continue

    # Build a document URL the user can open directly
    doc_url = f"{base}/documents/{new_did}/w/{new_workspace_id}/e/{new_element_id}"

    print(f"✅ Successfully generated and filed: {wire_id}")
    print(f"  Document: {doc_url}")

    # Append the created document info to a local CSV for future reference
    try:
        with open('generated_drawings.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([wire_id, csv_part_number, new_did, new_workspace_id, new_element_id, doc_url])
    except Exception:
        # Non-fatal if logging fails
        pass
    
    # Pause for 1 second to respect API speed limits
    time.sleep(1)

print("-" * 50)
print("🎉 All 2D manufacturing drawings generated and filed successfully!")