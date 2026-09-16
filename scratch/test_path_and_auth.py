import re
from typing import Dict, Tuple

def resolve_path_variables(path: str, params_dict: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    if not path:
        return path, params_dict
        
    resolved_path = path
    remaining_params = dict(params_dict)
    
    for k, v in params_dict.items():
        if not k:
            continue
        curly_pattern = r'\{' + re.escape(k) + r'\}'
        colon_pattern = r':' + re.escape(k) + r'\b'
        
        replaced = False
        if re.search(curly_pattern, resolved_path):
            resolved_path = re.sub(curly_pattern, str(v), resolved_path)
            replaced = True
        elif re.search(colon_pattern, resolved_path):
            resolved_path = re.sub(colon_pattern, str(v), resolved_path)
            replaced = True
            
        if replaced:
            remaining_params.pop(k, None)
            
    return resolved_path, remaining_params

# Test 1: {tableId}
path1 = "/api/table/table-manager/detail/{tableId}"
params1 = {"tableId": "tbl_Hy", "page": "1"}
res_path1, rem_params1 = resolve_path_variables(path1, params1)
print("Test 1:")
print("  resolved_path:", res_path1)
print("  remaining_params:", rem_params1)
assert res_path1 == "/api/table/table-manager/detail/tbl_Hy"
assert rem_params1 == {"page": "1"}

# Test 2: :tableId
path2 = "/api/table/table-manager/detail/:tableId"
params2 = {"tableId": "tbl_Hy"}
res_path2, rem_params2 = resolve_path_variables(path2, params2)
print("Test 2:")
print("  resolved_path:", res_path2)
print("  remaining_params:", rem_params2)
assert res_path2 == "/api/table/table-manager/detail/tbl_Hy"
assert rem_params2 == {}

print("\nAll resolve_path_variables tests passed!")
