import os
import json
import requests

def main():
    # 1. Grab credentials from your .env file
    url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
    access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
    secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')
    
    auth = (access, secret)
    base = url.rstrip('/')

    # 2. Target the specific broken file from your URL
    # https://cad.onshape.com/documents/fc1441952898a249e924f974/w/b18dd9de5d6d06df5e03dc55/e/2149469f348284fa49075423
    broken_did = "fc1441952898a249e924f974"
    broken_wid = "b18dd9de5d6d06df5e03dc55"
    
    print("🔍 Starting Post-Mortem Diagnostic of Broken File...")
    
    report = []
    report.append("================ BROKEN FILE FORENSIC REPORT ================")
    report.append(f"Document ID: {broken_did}")
    report.append(f"Workspace ID: {broken_wid}\n")
    
    # --- A. Map Elements ---
    print("Fetching Elements...")
    elements_url = f"{base}/api/documents/d/{broken_did}/w/{broken_wid}/elements"
    r_elems = requests.get(elements_url, auth=auth, headers={"Accept": "application/json"})
    
    if r_elems.status_code != 200:
        print("Failed to fetch elements. Check API keys.")
        return
        
    elements = r_elems.json()
    asm_eid = None
    ps_eid = None
    
    report.append("--- ELEMENTS FOUND IN BROKEN FILE ---")
    for el in elements:
        e_type = (el.get('type') or el.get('elementType') or '').lower()
        e_name = el.get('name', '')
        e_id = el.get('id')
        report.append(f"Type: {e_type:15} | Name: {e_name:30} | ID: {e_id}")
        
        if e_type == 'assembly' and 'bom' not in e_name.lower():
            asm_eid = e_id
        elif e_type == 'part studio':
            ps_eid = e_id
            
    report.append("\n")

    # --- B. Analyze Assembly State ---
    if asm_eid:
        print(f"Analyzing Assembly ({asm_eid})...")
        report.append(f"--- 1. ASSEMBLY CONFIGURATION STATE ({asm_eid}) ---")
        cfg_url = f"{base}/api/elements/d/{broken_did}/w/{broken_wid}/e/{asm_eid}/configuration"
        r_cfg = requests.get(cfg_url, auth=auth, headers={"Accept": "application/json"})
        if r_cfg.status_code == 200:
            report.append(json.dumps(r_cfg.json(), indent=2))
            
        report.append(f"\n--- 2. ASSEMBLY INSTANCES & SUPPRESSION STATE ---")
        # This tells us if the connectors are actually suppressed in the assembly
        def_url = f"{base}/api/assemblies/d/{broken_did}/w/{broken_wid}/e/{asm_eid}"
        r_def = requests.get(def_url, auth=auth, headers={"Accept": "application/json"})
        if r_def.status_code == 200:
            asm_data = r_def.json()
            instances = asm_data.get("rootAssembly", {}).get("instances", [])
            clean_instances = []
            for inst in instances:
                clean_instances.append({
                    "id": inst.get("id"),
                    "name": inst.get("name"),
                    "isSuppressed": inst.get("isSuppressed", False),
                    "configuration": inst.get("configuration", "None")
                })
            report.append(json.dumps(clean_instances, indent=2))
    
    report.append("\n")

    # --- C. Analyze Part Studio State ---
    if ps_eid:
        print(f"Analyzing Part Studio ({ps_eid})...")
        report.append(f"--- 3. PART STUDIO CONFIGURATION STATE ({ps_eid}) ---")
        # This tells us if the Assembly successfully pushed the length down to the Part Studio
        cfg_url = f"{base}/api/elements/d/{broken_did}/w/{broken_wid}/e/{ps_eid}/configuration"
        r_cfg = requests.get(cfg_url, auth=auth, headers={"Accept": "application/json"})
        if r_cfg.status_code == 200:
            report.append(json.dumps(r_cfg.json(), indent=2))
            
        report.append(f"\n--- 4. PART STUDIO FEATURES (Why did the wire break?) ---")
        # This pulls the exact geometry generation errors
        feat_url = f"{base}/api/partstudios/d/{broken_did}/w/{broken_wid}/e/{ps_eid}/features"
        r_feat = requests.get(feat_url, auth=auth, headers={"Accept": "application/json"})
        if r_feat.status_code == 200:
            feats = r_feat.json().get('features', [])
            clean_feats = []
            for f in feats:
                msg = f.get("message", {})
                clean_feats.append({
                    "name": msg.get("name", "Unknown"),
                    "type": msg.get("featureType", "Unknown"),
                    "suppressed": msg.get("suppressed", False),
                    "featureStatus": msg.get("featureStatus", "UNKNOWN")
                })
            report.append(json.dumps(clean_feats, indent=2))

    # --- D. Write to File ---
    output_filename = 'broken_file_diagnostic.txt'
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
        
    print(f"\n✅ Diagnostic complete! Data saved to '{output_filename}'.")
    print("Please copy and paste the ENTIRE contents of that text file into your next message to Gemini.")

if __name__ == "__main__":
    main()