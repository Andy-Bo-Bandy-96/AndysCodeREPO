# Onshape Cable Script - API Fixes Summary

## Problem Solved
The script was failing to update configuration parameters in Onshape documents due to incorrect API payload format.

### Error Progression & Discovery
1. **First Error**: "Invalid class type for object. Check the btType." with `BTConfigurationUpdateCall` root type
2. **Second Attempt**: Trying `BTConfigurationResponse-2019` root type → same error
3. **Third Attempt**: Removing root btType entirely → `BTWeirdStringValueException` 
4. **ROOT CAUSE FOUND**: Value format was "121.746 mm" when API only accepts numeric value "121.746"

## Solution: Correct API Payload Format

### What DOESN'T Work ❌
```json
{
  "btType": "BTConfigurationUpdateCall",  // WRONG - not a valid serialization class
  "currentConfiguration": [...]
}

{
  "btType": "BTConfigurationResponse-2019",  // WRONG - only for GET responses
  "currentConfiguration": [...]
}

{
  "currentConfiguration": [
    {
      "parameterId": "WireLength",
      "value": "121.746 mm"  // WRONG - API rejects units, wants numeric only
    }
  ]
}
```

### What WORKS ✅
```json
{
  "currentConfiguration": [
    {
      "btType": "BTMParameterQuantity-147",  // REQUIRED - tells API the concrete type
      "parameterId": "WireLength",            // REQUIRED - exact parameter ID from GET
      "value": "121.746"                      // REQUIRED - numeric value only, no units
    }
  ]
}
```

## Critical Rules for Onshape Configuration Updates

1. **NO root `btType`** - omit it entirely from the root object
2. **Parameter `btType` IS required** - this tells the API the concrete class (BTMParameterQuantity-147, BTMParameterString-148, etc.)
3. **Value format depends on parameter type**:
   - **Quantity parameters** (WireLength): numeric only → `"121.746"`
   - **String parameters** (Connector_A): string value → `"sv1.25-4Fork"`
4. **Only send fields being changed** - keep payload minimal
5. **Parameter ID must match exactly** - use the ID from GET configuration response

## Script Changes Made

### Updated Logic
- Changed value handling to strip "mm" suffix and send numeric-only values
- Improved element discovery to find ALL elements (Part Studio, Assembly, Drawing, BOM) without stopping early
- Enhanced error messages with debugging hints
- Better handling of 404 errors from Assembly and Drawing endpoints (non-fatal)

### File: `generate_wires.py`
**Lines ~120-160**: Part Studio configuration update
- Extracts numeric value from length string
- Builds minimal payload with parameter btType
- Properly handles parameter matching

**Lines ~190-240**: Assembly configuration update  
- Uses same minimal payload structure
- Gracefully handles 404 errors

**Lines ~200-250**: Element discovery
- Scans all elements before selecting
- Properly identifies Part Studio, Assembly, and Drawing tabs

## Testing Results

✅ **Success Metrics**:
- Part Studio configuration updates return HTTP 200
- Parameters properly updated with new values
- Document creation and copying works
- CSV logging successful
- Metadata updates successful

⚠️ **Non-Critical Issues**:
- Assembly configuration may return 404 (template-dependent)
- Drawing sync may return 404 (optional feature)
- These don't block document creation

## How to Verify It's Working

1. Run the script:
   ```bash
   op run --env-file=".env" -- python3 generate_wires.py
   ```

2. Look for "Response Status: 200" in Part Studio configuration update section

3. Check the generated Onshape documents to verify:
   - Document was created in target folder
   - Configuration parameters were updated
   - Part Number metadata was set

## Next Steps if Issues Persist

If configuration updates still fail:
1. Check parameter IDs - run GET configuration to see actual IDs
2. Verify parameter types (Quantity vs String)
3. Check if assembly has different parameter names
4. Test with empty payload `{}` to see if bare endpoint works

## References
- [Onshape API Configuration Guide](https://onshape-public.github.io/docs/api-adv/configs/)
- [updateConfiguration Endpoint](https://cad.onshape.com/glassworks/explorer/#/Element/updateConfiguration)
