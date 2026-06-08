import os
import json
import requests

def main():
    # 1. Grab credentials
    url = os.getenv("ONSHAPE_BASE_URL", "https://cad.onshape.com").strip(' "\'\n\r')
    access = os.getenv("ONSHAPE_ACCESS_KEY", "").strip(' "\'\n\r')
    secret = os.getenv("ONSHAPE_SECRET_KEY", "").strip(' "\'\n\r')
    auth = (access, secret)
    base = url.rstrip('/')

    # 2. Target the exact file you just generated
    broken_did = "7ce914839d085d5b5f7e9b82"
    broken_wid = "80e3bbb52f9989f06cb60b65"
    
    print("🔍 Extracting absolute core data from the broken file...")
    report = []
    
    # --- A. Find Assembly ---
    r_elems = requests.get(f"{base}/api/documents/d/{broken_did}/w/{broken_wid}/elements", auth=auth)
    if r_elems.status_code != 200:
        print("Failed to authenticate.")
        return
        
    elements = r_elems.json()
    asm_id = None
    for el in elements:
        if (el.get('type') or '').lower() == 'assembly' and 'bom' not in el.get('name', '').lower():
            asm_id = el.get('id')
            break
            
    if not asm_id:
        print("No assembly found!")
        return

    # --- B. Get Assembly Configuration Schema ---
    report.append("=== 1. ASSEMBLY CONFIGURATION SCHEMAS ===")
    r_cfg = requests.get(f"{base}/api/elements/d/{broken_did}/w/{broken_wid}/e/{asm_id}/configuration", auth=auth)
    report.append(json.dumps(r_cfg.json(), indent=2))
    
    # --- C. Get Assembly Definition (Instances & Mappings) ---
    report.append("\n=== 2. ASSEMBLY DEFINITION (INSTANCES) ===")
    r_def = requests.get(f"{base}/api/assemblies/d/{broken_did}/w/{broken_wid}/e/{asm_id}", auth=auth)
    if r_def.status_code == 200:
        asm_data = r_def.json()
        instances = asm_data.get("rootAssembly", {}).get("instances", [])
        
        clean_instances = []
        for inst in instances:
            clean_instances.append({
                "name": inst.get("name"),
                "configuration": inst.get("configuration", "NO CONFIGURATION SET"),
                "isSuppressed": inst.get("isSuppressed", False)
            })
        report.append(json.dumps(clean_instances, indent=2))

    # --- D. Check Assembly Features (Suppression Rules) ---
    report.append("\n=== 3. ASSEMBLY FEATURES (SUPPRESSION RULES) ===")
    r_feat = requests.get(f"{base}/api/assemblies/d/{broken_did}/w/{broken_wid}/e/{asm_id}/features", auth=auth)
    if r_feat.status_code == 200:
        feats = r_feat.json().get('features', [])
        clean_feats = []
        for f in feats:
            msg = f.get("message", {})
            clean_feats.append({
                "name": msg.get("name"),
                "suppressed": msg.get("suppressed")
            })
        report.append(json.dumps(clean_feats, indent=2))

    # Save to file
    with open('final_debug_dump.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
        
    print("\n✅ Diagnostic complete! Data saved to 'final_debug_dump.txt'.")
    print("Paste the exact contents of that file here.")

if __name__ == "__main__":
    main()