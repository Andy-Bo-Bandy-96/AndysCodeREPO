#!/usr/bin/env python3
"""
Diagnostic script to understand template structure:
- What's in /configuration endpoint?
- What's in /variables endpoint?
- Are the parameters stored as variables or configuration inputs?
"""

import os
import requests
import json
from requests.auth import HTTPBasicAuth

# Get env vars
base = os.getenv('ONSHAPE_BASE_URL', 'https://cad.onshape.com').rstrip('/')
access_key = os.getenv('ONSHAPE_ACCESS_KEY', '')
secret_key = os.getenv('ONSHAPE_SECRET_KEY', '')
template_did = os.getenv('TEMPLATE_DID', '')
template_wid = os.getenv('TEMPLATE_WID', '')
template_eid = os.getenv('TEMPLATE_EID', '')

auth = HTTPBasicAuth(access_key, secret_key)

print(f"🔍 TEMPLATE DIAGNOSTICS")
print(f"Template: {template_did} / {template_wid} / {template_eid}")
print(f"Base URL: {base}")
print()

# 1. Check /configuration endpoint (Configuration inputs/options)
print("=" * 60)
print("1️⃣  CHECKING /configuration ENDPOINT (Configuration inputs)")
print("=" * 60)
config_url = f"{base}/api/v6/elements/d/{template_did}/w/{template_wid}/e/{template_eid}/configuration"
print(f"URL: {config_url}")
print()

try:
    resp = requests.get(config_url, auth=auth, headers={"Accept": "application/json"})
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        current_config = data.get('currentConfiguration', [])
        print(f"currentConfiguration items: {len(current_config)}")
        if current_config:
            for item in current_config:
                print(f"  - parameterId: {item.get('parameterId')}")
                print(f"    value: {item.get('value')}")
                print(f"    btType: {item.get('btType')}")
                print()
        else:
            print("  (empty)")
        print()
        print("Full response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print()
print()

# 2. Check /variables endpoint (Assembly variables)
print("=" * 60)
print("2️⃣  CHECKING /variables ENDPOINT (Assembly variables)")
print("=" * 60)
variables_url = f"{base}/api/v6/elements/d/{template_did}/w/{template_wid}/e/{template_eid}/variables"
print(f"URL: {variables_url}")
print()

try:
    resp = requests.get(variables_url, auth=auth, headers={"Accept": "application/json"})
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        variables = data.get('variables', [])
        print(f"variables items: {len(variables)}")
        if variables:
            for var in variables:
                print(f"  - name: {var.get('name')}")
                print(f"    value: {var.get('value')}")
                print(f"    type: {var.get('type')}")
                print()
        else:
            print("  (empty)")
        print()
        print("Full response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print()
print()

# 3. List all elements again to confirm we have the right assembly
print("=" * 60)
print("3️⃣  VERIFYING TEMPLATE ELEMENTS")
print("=" * 60)
elements_url = f"{base}/api/documents/d/{template_did}/w/{template_wid}/elements"
print(f"URL: {elements_url}")
print()

try:
    resp = requests.get(elements_url, auth=auth, headers={"Accept": "application/json"})
    if resp.status_code == 200:
        items = resp.json()
        for item in items:
            el_type = (item.get('type') or '').lower()
            el_name = (item.get('name') or '').lower()
            el_id = item.get('id')
            is_target = "← TEMPLATE_EID" if el_id == template_eid else ""
            print(f"  {el_type:20} | {el_name:35} | {el_id:30} {is_target}")
    else:
        print(f"Error: {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")
