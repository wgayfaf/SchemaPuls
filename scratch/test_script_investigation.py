import sys
sys.path.insert(0, 'backend')
from app.services.action_engine import execute_pre_actions, execute_post_actions

print("=== 实验 1: JS 脚本中直接写 var / const / let 局部变量 ===")
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "javascript",
        "value": "var my_token = 'hello_123'; const a = 1; b = 2;"
    }],
    body='{"token": "{{my_token}}"}'
)
print("updated_env:", updated_env)
print("body rendered:", body)

print("\n=== 实验 2: JS 脚本中使用 pm.environment.set / pm.variables.set ===")
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "javascript",
        "value": "pm.environment.set('my_token', 'hello_123');"
    }],
    body='{"token": "{{my_token}}"}'
)
print("updated_env:", updated_env)
print("body rendered:", body)

print("\n=== 实验 3: 表单设置变量 set_variable ===")
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "set_variable",
        "key": "my_token",
        "value": "hello_123"
    }],
    body='{"token": "{{my_token}}"}'
)
print("updated_env:", updated_env)
print("body rendered:", body)

print("\n=== 实验 4: Python 脚本中直接写 a = '123' 局部变量 ===")
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "custom_script",
        "value": "my_token = 'hello_123'"
    }],
    body='{"token": "{{my_token}}"}'
)
print("updated_env:", updated_env)
print("body rendered:", body)

print("\n=== 实验 5: Python 脚本中写 environment['my_token'] = 'hello_123' ===")
_, _, body, _, variables, updated_env = execute_pre_actions(
    pre_actions=[{
        "enabled": True,
        "type": "custom_script",
        "value": "environment['my_token'] = 'hello_123'"
    }],
    body='{"token": "{{my_token}}"}'
)
print("updated_env:", updated_env)
print("body rendered:", body)
