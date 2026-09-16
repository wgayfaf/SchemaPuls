import sys
sys.path.insert(0, 'backend')
import json, sqlite3
from app.services.action_engine import execute_pre_actions, execute_post_actions

print("=== 验证用例 1: 重复 const/let 声明 (用户实际遇到的 RSA 脚本场景) ===")
duplicate_script = """
const jsrsasign = require('jsrsasign');
const a = 'first';
const jsrsasign = require('jsrsasign');
const a = 'second';
pm.environment.set('ENCRYPTED_PASSWORD', 'enc_val_123');
"""
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "javascript",
        "value": duplicate_script
    }],
    body='{"pwd": {{ENCRYPTED_PASSWORD}}, "with_space": {{ ENCRYPTED_PASSWORD }}}'
)
print("  updated_env:", updated_env)
print("  script_error:", variables.get("_script_error"))
print("  body rendered:", body)
assert "ENCRYPTED_PASSWORD" in updated_env
assert body == '{"pwd": enc_val_123, "with_space": enc_val_123}'
print("  => 用例 1 通过！")

print("\n=== 验证用例 2: 原生 JS 直接全局赋值 (无 pm.set) ===")
plain_js_script = """
my_token = 'global_token_999';
var another_var = 'var_token_888';
"""
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "javascript",
        "value": plain_js_script
    }],
    body='{"token": "{{my_token}}", "another": "{{another_var}}"}'
)
print("  updated_env:", updated_env)
print("  script_error:", variables.get("_script_error"))
print("  body rendered:", body)
assert updated_env.get("my_token") == "global_token_999"
assert updated_env.get("another_var") == "var_token_888"
assert body == '{"token": "global_token_999", "another": "var_token_888"}'
print("  => 用例 2 通过！")

print("\n=== 验证用例 3: Python 脚本直接赋值 ===")
python_script = """
my_py_token = 'py_token_777'
"""
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "custom_script",
        "value": python_script
    }],
    body='{"py_token": "{{my_py_token}}"}'
)
print("  updated_env:", updated_env)
print("  body rendered:", body)
assert updated_env.get("my_py_token") == "py_token_777"
assert body == '{"py_token": "py_token_777"}'
print("  => 用例 3 通过！")

print("\n=== 验证用例 4: 针对数据库中真实 ApiProbe id=1 进行端到端验证 ===")
conn = sqlite3.connect('backend/monitor.db')
c = conn.cursor()
row = c.execute('SELECT pre_actions, http_body FROM api_probes WHERE id=1').fetchone()
pre_actions = json.loads(row[0])
real_body = row[1]
_, _, rendered_body, _, variables, updated_env = execute_pre_actions(
    pre_actions=pre_actions,
    body=real_body,
    environment_variables={}
)
print("  updated_env keys:", list(updated_env.keys()))
print("  script_error:", variables.get("_script_error"))
print("  rendered_body:\n", rendered_body)
assert "ENCRYPTED_PASSWORD" in updated_env
assert "{{ENCRYPTED_PASSWORD}}" not in rendered_body
print("  => 用例 4 (真实 ApiProbe 1) 100% 完美通过！")
