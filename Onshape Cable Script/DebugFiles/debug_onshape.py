import os
import json
import requests

def main():
    # 1. Grab variables
    url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
    access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
    secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')
    did = os.getenv("TEMPLATE_DID", "").strip(' "\'\n\r')
    wid = os.getenv("TEMPLATE_WID", "").strip(' "\'\n\r')
    
    auth = (access, secret)
    base = url.rstrip('/')
    
    print("🔍 Starting Deep Diagnostic of Master Template...")
    
    report = []
    report.append("================ ONSHAPE DEEP DIAGNOSTIC REPORT ================")
    report.append(f"Document ID: {did}")
    report.append(f"Workspace ID: {wid}\n")
    
    # 2. Get Elements
    print("Fetching Elements...")
    elements_url = f"{base}/api/documents/d/{did}/w/{wid}/elements"
    r_elems = requests.get(elements_url, auth=auth, headers={"Accept": "application/json"})
    
    if r_elems.status_code != 200:
        print("Failed to fetch elements. Check API keys and IDs.")
        return
        
    elements = r_elems.json()
    asm_eid = None
    ps_eid = None
    
    report.append("--- ELEMENTS FOUND ---")
    for el in elements:
        e_type = (el.get('type') or el.get('elementType') or '').lower()
        e_name = el.get('name', '')
        e_id = el.get('id')
        report.append(f"Type: {e_type:15} | Name: {e_name:30} | ID: {e_id}")
        
        if e_type == 'assembly' and 'bom' not in e_name.lower() and 'bill' not in e_name.lower():
            asm_eid = e_id
        elif e_type == 'part studio':
            ps_eid = e_id
            
    report.append("\n")

    # 3. Analyze Assembly
    if asm_eid:
        print(f"Analyzing Assembly ({asm_eid})...")
        report.append(f"--- ASSEMBLY CONFIGURATION ({asm_eid}) ---")
        cfg_url = f"{base}/api/elements/d/{did}/w/{wid}/e/{asm_eid}/configuration"
        r_cfg = requests.get(cfg_url, auth=auth, headers={"Accept": "application/json"})
        if r_cfg.status_code == 200:
            report.append(json.dumps(r_cfg.json(), indent=2))
        else:
            report.append(f"Failed to fetch assembly config: {r_cfg.status_code}")
            
        report.append(f"\n--- ASSEMBLY DEFINITION (Instances & References) ---")
        def_url = f"{base}/api/assemblies/d/{did}/w/{wid}/e/{asm_eid}"
        r_def = requests.get(def_url, auth=auth, headers={"Accept": "application/json"})
        if r_def.status_code == 200:
            asm_data = r_def.json()
            # Only keep instances to keep the log readable
            report.append(json.dumps({"instances": asm_data.get("instances", [])}, indent=2))
    
    report.append("\n")

    # 4. Analyze Part Studio (CRITICAL for Geometry & Suppression)
    if ps_eid:
        print(f"Analyzing Part Studio ({ps_eid})...")
        report.append(f"--- PART STUDIO CONFIGURATION ({ps_eid}) ---")
        cfg_url = f"{base}/api/elements/d/{did}/w/{wid}/e/{ps_eid}/configuration"
        r_cfg = requests.get(cfg_url, auth=auth, headers={"Accept": "application/json"})
        if r_cfg.status_code == 200:
            report.append(json.dumps(r_cfg.json(), indent=2))
        else:
            report.append(f"Failed to fetch part studio config: {r_cfg.status_code}")
            
        report.append(f"\n--- PART STUDIO FEATURES (Geometry & Suppression Rules) ---")
        feat_url = f"{base}/api/partstudios/d/{did}/w/{wid}/e/{ps_eid}/features"
        r_feat = requests.get(feat_url, auth=auth, headers={"Accept": "application/json"})
        if r_feat.status_code == 200:
            # We want to see how the features are structured and if there are suppression states
            feats = r_feat.json().get('features', [])
            clean_feats = []
            for f in feats:
                clean_feats.append({
                    "name": f.get("message", {}).get("name", "Unknown"),
                    "type": f.get("message", {}).get("featureType", "Unknown"),
                    "suppressed": f.get("message", {}).get("suppressed", False)
                })
            report.append(json.dumps(clean_feats, indent=2))
        else:
            report.append(f"Failed to fetch part studio features: {r_feat.status_code}")

    # 5. Write to file
    with open('onshape_debug_dump.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
        
    print("\n✅ Diagnostic complete! Data saved to 'onshape_debug_dump.txt'.")
    print("Please copy and paste the ENTIRE contents of that text file into your next message to Gemini.")

if __name__ == "__main__":
    main()