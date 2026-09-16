import os, sys
sys.path.insert(0, os.path.abspath("backend"))
from sqlmodel import Session, select, create_engine
from app.models import Environment, ServiceGroup, MachineNode, ApiProbe
from app.services.action_engine import execute_pre_actions, execute_post_actions

engine = create_engine('sqlite:///backend/monitor.db')
with Session(engine) as session:
    env = session.get(Environment, 1)
    print('Initial env variables:', env.variables)
    
    pre_actions = [
        {'enabled': True, 'type': 'set_variable', 'key': 'PRE_VAR_KEY', 'value': 'pre_var_val'},
        {'enabled': True, 'type': 'javascript', 'value': 'pm.variables.set("JS_VAR_KEY", "js_var_val"); pm.environment.set("ENV_VAR_KEY", "env_var_val");'}
    ]
    
    final_headers, final_params, final_body, final_path, variables, pre_updated_env = execute_pre_actions(
        pre_actions=pre_actions,
        headers={},
        params={},
        environment_variables=env.variables
    )
    
    print('\nAfter execute_pre_actions:')
    print('pre_updated_env:', pre_updated_env)
    print('variables has PRE_VAR_KEY?', 'PRE_VAR_KEY' in variables)
    print('pre_updated_env has PRE_VAR_KEY?', 'PRE_VAR_KEY' in pre_updated_env)
    print('pre_updated_env has JS_VAR_KEY?', 'JS_VAR_KEY' in pre_updated_env)
    print('pre_updated_env has ENV_VAR_KEY?', 'ENV_VAR_KEY' in pre_updated_env)

    post_actions = [
        {'enabled': True, 'type': 'extract_variable', 'key': 'TOKEN_FROM_EXTRACT', 'expression': 'data.token'},
        {'enabled': True, 'type': 'javascript', 'value': 'pm.variables.set("POST_JS_VAR", "post_js_val"); pm.environment.set("POST_ENV_VAR", "post_env_val");'}
    ]

    passed, assertions, extracted_vars, post_updated_env = execute_post_actions(
        post_actions=post_actions,
        status_code=200,
        latency_ms=50,
        response_headers={},
        response_data={'data': {'token': 'extracted_token_abc'}},
        response_text='{"data": {"token": "extracted_token_abc"}}',
        environment_variables={}
    )

    print('\nAfter execute_post_actions:')
    print('post_updated_env:', post_updated_env)
    print('extracted_vars:', extracted_vars)
