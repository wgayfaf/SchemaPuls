import os
import sys
import json
from fastapi.testclient import TestClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
sys.path.insert(0, backend_dir)

from app.main import app
from app.database import engine, init_db
from sqlmodel import Session, select
from app.models import MachineNode, ApiProbe, Environment, ServiceGroup
from app.services.action_engine import (
    execute_pre_actions,
    execute_post_actions,
    get_nested_value
)

def test_action_engine_unit():
    print("==================================================")
    print("   1. 测试前置操作与后置操作内核 (ActionEngine)")
    print("==================================================")
    
    # 1.1 测试前置操作
    pre_actions = [
        {"enabled": True, "type": "set_variable", "key": "app_ver", "value": "v2.0.1"},
        {"enabled": True, "type": "set_variable", "key": "dyn_ts", "value": "{{$timestamp}}"},
        {"enabled": True, "type": "inject_header", "key": "X-Custom-Client", "value": "SchemaPulse_{{app_ver}}"},
        {"enabled": True, "type": "inject_param", "key": "ts", "value": "{{dyn_ts}}"},
        {"enabled": True, "type": "custom_script", "key": "", "value": "variables['sign'] = 'SIGN_' + variables['app_ver']"}
    ]
    headers, params, body, path, vars_out = execute_pre_actions(
        pre_actions=pre_actions,
        headers={"Accept": "application/json"},
        params={"page": "1"},
        body='{"version": "{{app_ver}}", "sign": "{{sign}}"}',
        path="/api/{{app_ver}}/users",
        auth_token="token_xyz"
    )
    
    assert vars_out["app_ver"] == "v2.0.1"
    assert vars_out["sign"] == "SIGN_v2.0.1"
    assert headers["X-Custom-Client"] == "SchemaPulse_v2.0.1"
    assert "ts" in params
    assert path == "/api/v2.0.1/users"
    assert '"version": "v2.0.1"' in body
    assert '"sign": "SIGN_v2.0.1"' in body
    print(f"[OK] 前置操作与变量多层渲染通过: headers={headers}, params={params}, path={path}, sign={vars_out['sign']}")

    # 1.2 测试嵌套路径提取
    data = {
        "code": 200,
        "message": "success",
        "data": {
            "token": "tok_998877",
            "user": {
                "id": 1001,
                "name": "Alice",
                "roles": ["admin", "tester"]
            }
        }
    }
    f1, v1 = get_nested_value(data, "code")
    assert f1 and v1 == 200
    f2, v2 = get_nested_value(data, "data.user.id")
    assert f2 and v2 == 1001
    f3, v3 = get_nested_value(data, "data.user.roles[1]")
    assert f3 and v3 == "tester"
    print(f"[OK] 嵌套数据提取测试通过: code={v1}, user.id={v2}, role[1]={v3}")

    # 1.3 测试后置操作断言与提取
    post_actions = [
        {"enabled": True, "name": "状态码为200", "type": "assert_status_code", "operator": "equals", "target_value": "200"},
        {"enabled": True, "name": "耗时小于1000ms", "type": "assert_latency", "operator": "less_than", "target_value": "1000"},
        {"enabled": True, "name": "code为200", "type": "assert_json_path", "expression": "code", "operator": "equals", "target_value": "200"},
        {"enabled": True, "name": "用户名称为Alice", "type": "assert_json_path", "expression": "data.user.name", "operator": "equals", "target_value": "Alice"},
        {"enabled": True, "name": "响应包含success", "type": "assert_body_contains", "operator": "contains", "target_value": "success"},
        {"enabled": True, "name": "提取Token", "type": "extract_variable", "expression": "data.token", "target_value": "extractedToken"}
    ]
    all_passed, results, extracted = execute_post_actions(
        post_actions=post_actions,
        status_code=200,
        latency_ms=120.5,
        response_headers={"content-type": "application/json; charset=utf-8"},
        response_data=data,
        context_variables=vars_out
    )
    assert all_passed is True
    assert len(results) == 6
    assert extracted.get("extractedToken") == "tok_998877"
    for r in results:
        assert r["passed"] is True, f"断言失败: {r}"
    print(f"[OK] 后置操作断言全部通过，成功提取变量: {extracted}")

    # 1.4 测试断言失败检测
    fail_actions = [
        {"enabled": True, "name": "状态码应为500", "type": "assert_status_code", "operator": "equals", "target_value": "500"},
        {"enabled": True, "name": "耗时超速断言", "type": "assert_latency", "operator": "less_than", "target_value": "50"}
    ]
    fail_passed, fail_res, _ = execute_post_actions(
        post_actions=fail_actions,
        status_code=200,
        latency_ms=120.5,
        response_data=data
    )
    assert fail_passed is False
    assert fail_res[0]["passed"] is False
    assert fail_res[1]["passed"] is False
    print(f"[OK] 断言异常捕获机制验证通过: fail_passed={fail_passed}")

    # 1.5 测试 JavaScript (Postman JS) 预脚本与断言
    js_pre_actions = [
        {"enabled": True, "type": "javascript", "key": "", "value": """
            pm.variables.set('ts_now', Date.now());
            pm.variables.set('sign_hash', 'SHA_' + (1000 + 24));
            pm.variables.set('auth_basic', btoa('admin:secret123'));
            pm.request.headers.add({ key: 'X-App-Id', value: 'QuickJS_App' });
            variables['direct_var'] = 'from_direct';
            params['page'] = '99';
        """}
    ]
    js_headers, js_params, js_body, js_path, js_vars = execute_pre_actions(
        pre_actions=js_pre_actions,
        headers={"Content-Type": "application/json"},
        params={"page": "1"},
        body='{"sign": "{{sign_hash}}", "auth": "{{auth_basic}}"}',
        path="/api/check"
    )
    assert "ts_now" in js_vars
    assert js_vars["sign_hash"] == "SHA_1024"
    assert js_vars["auth_basic"] == "YWRtaW46c2VjcmV0MTIz"
    assert js_headers["X-App-Id"] == "QuickJS_App"
    assert js_params["page"] == "99"
    assert '"sign": "SHA_1024"' in js_body
    assert '"auth": "YWRtaW46c2VjcmV0MTIz"' in js_body
    print(f"[OK] JavaScript (Postman JS) 前置操作执行通过: sign={js_vars['sign_hash']}, auth={js_vars['auth_basic']}")

    js_post_actions = [
        {"enabled": True, "name": "Postman JS 测试断言", "type": "javascript", "value": """
            pm.test("Status is 200", function() {
                pm.response.to.have.status(200);
            });
            var json = pm.response.json();
            pm.test("Code is 200", function() {
                pm.expect(json.code).to.equal(200);
            });
            pm.test("User name is Alice", function() {
                pm.expect(json.data.user.name).to.equal("Alice");
            });
            pm.environment.set("js_extracted_user", json.data.user.name);
        """}
    ]
    js_all_passed, js_results, js_extracted = execute_post_actions(
        post_actions=js_post_actions,
        status_code=200,
        latency_ms=88.0,
        response_data=data,
        context_variables=js_vars
    )
    assert js_all_passed is True
    assert len(js_results) == 3
    assert all(r["passed"] for r in js_results)
    assert js_extracted.get("js_extracted_user") == "Alice"
    print(f"[OK] JavaScript (Postman Tests) 后置断言测试通过: results={len(js_results)}, extracted={js_extracted}")


def test_api_test_run_with_actions():
    print("\n==================================================")
    print("   2. 测试 API 在线调试端点 (/api/apis/test-run)")
    print("==================================================")
    init_db()
    client = TestClient(app)

    with Session(engine) as session:
        env = session.exec(select(Environment)).first()
        if not env:
            env = Environment(name="测试环境", order_num=1)
            session.add(env)
            session.commit()
            session.refresh(env)

        grp = session.exec(select(ServiceGroup).where(ServiceGroup.environment_id == env.id)).first()
        if not grp:
            grp = ServiceGroup(environment_id=env.id, name="测试集群")
            session.add(grp)
            session.commit()
            session.refresh(grp)

        machine = session.exec(select(MachineNode).where(MachineNode.host == "httpbin.org")).first()
        if not machine:
            machine = MachineNode(
                group_id=grp.id,
                name="HttpBin节点",
                host="httpbin.org",
                port=80,
                is_active=True
            )
            session.add(machine)
            session.commit()
            session.refresh(machine)
        m_id = machine.id

    # 调试测试：前置操作注入请求头与参数，后置操作断言状态码
    payload = {
        "machine_id": m_id,
        "http_method": "GET",
        "http_path": "/get",
        "http_params": [
            {"enabled": True, "key": "client", "value": "{{my_app}}"}
        ],
        "http_headers": [
            {"enabled": True, "key": "X-Client-Trace", "value": "{{$uuid}}"}
        ],
        "pre_actions": [
            {"enabled": True, "type": "set_variable", "key": "my_app", "value": "SchemaPulseTest"},
            {"enabled": True, "type": "inject_header", "key": "X-Pre-Header", "value": "PreValue_{{my_app}}"},
            {"enabled": True, "type": "javascript", "value": "pm.variables.set('js_flag', 'FLAG_' + 888); pm.request.headers.add({ key: 'X-JS-Header', value: 'JS_HEADER_OK' });"}
        ],
        "post_actions": [
            {"enabled": True, "name": "HTTP 状态码等于 200", "type": "assert_status_code", "operator": "equals", "target_value": "200"},
            {"enabled": True, "name": "HTTP 状态码在 2xx 范围", "type": "assert_status_code", "operator": "in_2xx", "target_value": ""},
            {"enabled": True, "name": "耗时小于 10000ms", "type": "assert_latency", "operator": "less_than", "target_value": "10000"},
            {"enabled": True, "name": "JS 脚本测试断言", "type": "javascript", "value": "pm.test('Postman JS OK', function() { pm.expect(pm.response.code).to.equal(200); });"}
        ]
    }

    res = client.post("/api/apis/test-run", json=payload)
    assert res.status_code == 200, f"test-run 返回错误: {res.text}"
    data = res.json()
    print("DEBUG test-run data:", data.get("status_code"), data.get("error_message"), data.get("assertions_summary"), data.get("assertions_result"))
    assert "assertions_summary" in data
    assert "assertions_result" in data
    assert data["rendered_headers"].get("X-Pre-Header") == "PreValue_SchemaPulseTest"
    assert data["rendered_headers"].get("X-JS-Header") == "JS_HEADER_OK"
    assert data["rendered_params"].get("client") == "SchemaPulseTest"
    assert data["assertions_summary"]["total"] == 4
    if data["status_code"] == 200:
        assert data["assertions_summary"]["passed_count"] == 4
    else:
        print(f"[WARN] 外部 httpbin.org 网络连接返回状态码 {data['status_code']} / {data.get('error_message')}")

    print(f"[OK] /api/apis/test-run 执行完成:")
    print(f"     状态码: {data['status_code']}, 断言总数: {data['assertions_summary']['total']}, 通过数: {data['assertions_summary']['passed_count']}")
    print(f"     渲染后 Headers: {data['rendered_headers']}")
    print(f"     渲染后 Params: {data['rendered_params']}")


def test_body_json_with_pre_action_parameters():
    print("\n==================================================")
    print("   2.5 测试 Body JSON 充分应用前置操作参数与脚本改写")
    print("==================================================")
    # 1. 测试单元级：变量池融合替换 (包括 set_variable, inject_param, inject_header, JavaScript)
    pre_actions = [
        {"enabled": True, "type": "set_variable", "key": "userId", "value": "10086"},
        {"enabled": True, "type": "inject_param", "key": "deptCode", "value": "DEV_TEAM"},
        {"enabled": True, "type": "inject_header", "key": "X-Tenant-Id", "value": "TENANT_999"},
        {"enabled": True, "type": "javascript", "value": """
            pm.variables.set('dyn_salt', 'SALT_' + 12345);
        """}
    ]
    raw_body = json.dumps({
        "uid": "{{userId}}",
        "dept": "{{deptCode}}",
        "tenant": "{{X-Tenant-Id}}",
        "salt": "{{dyn_salt}}",
        "timestamp": "{{$timestamp}}"
    })
    final_headers, final_params, final_body, final_path, variables = execute_pre_actions(
        pre_actions=pre_actions,
        headers={"Content-Type": "application/json"},
        params={},
        body=raw_body,
        path="/api/users"
    )
    parsed_body = json.loads(final_body)
    assert parsed_body["uid"] == "10086", f"uid 未正确替换: {parsed_body}"
    assert parsed_body["dept"] == "DEV_TEAM", f"前置 inject_param 未能注入 Body: {parsed_body}"
    assert parsed_body["tenant"] == "TENANT_999", f"前置 inject_header 未能注入 Body: {parsed_body}"
    assert parsed_body["salt"] == "SALT_12345", f"JS 生成变量未能注入 Body: {parsed_body}"
    assert len(parsed_body["timestamp"]) >= 10, f"动态宏 $timestamp 未正确解析: {parsed_body}"
    print(f"[OK] Body JSON 变量池多源融合插值验证通过: {final_body}")

    # 2. 测试 JavaScript 直接通过 pm.request.body.update 改写 Body
    js_modify_body_action = [
        {"enabled": True, "type": "javascript", "value": """
            var currentBody = JSON.parse(pm.request.body.raw || '{}');
            currentBody.computed_hash = 'HASH_ABC';
            currentBody.status = 'ACTIVE';
            pm.request.body.update(currentBody);
        """}
    ]
    _, _, modified_body, _, _ = execute_pre_actions(
        pre_actions=js_modify_body_action,
        body='{"initial_val": 1}'
    )
    parsed_mod = json.loads(modified_body)
    assert parsed_mod["initial_val"] == 1
    assert parsed_mod["computed_hash"] == "HASH_ABC"
    assert parsed_mod["status"] == "ACTIVE"
    print(f"[OK] JS 脚本通过 pm.request.body.update 改写 Body 验证通过: {modified_body}")

    # 3. 测试 /api/apis/test-run 接口真实发包时 rendered_body 的返回
    client = TestClient(app)
    with Session(engine) as session:
        machine = session.exec(select(MachineNode)).first()
        m_id = machine.id

    run_payload = {
        "machine_id": m_id,
        "http_method": "POST",
        "http_path": "/post",
        "http_body_type": "json",
        "http_body": json.dumps({"client": "{{client_name}}", "action": "probe_test", "injected": "{{extra_key}}"}),
        "pre_actions": [
            {"enabled": True, "type": "set_variable", "key": "client_name", "value": "SchemaPulse_Bot"},
            {"enabled": True, "type": "inject_param", "key": "extra_key", "value": "EXTRA_VALUE_99"}
        ]
    }
    resp = client.post("/api/apis/test-run", json=run_payload)
    assert resp.status_code == 200, f"test-run 失败: {resp.text}"
    resp_data = resp.json()
    assert "rendered_body" in resp_data, "返回结果应包含 rendered_body"
    rb = json.loads(resp_data["rendered_body"])
    assert rb["client"] == "SchemaPulse_Bot"
    assert rb["injected"] == "EXTRA_VALUE_99"
    print(f"[OK] /api/apis/test-run 正确回传 rendered_body 并发送给目标接口: {resp_data['rendered_body']}")


def test_crypto_libraries_require():
    print("\n==================================================")
    print("   2.6 测试 require 机制与 jsrsasign / crypto-js / Buffer 密码学支持")
    print("==================================================")
    # 1. 测试用户提供的 jsrsasign RSA 加密脚本
    user_script = """
    const jsrsasign = require('jsrsasign');

    let publicKeyPEM = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy7YbsS0zH21A27PccrK99ee43Xf1hLlrmw3tO8U2DmO/mbc8mL/lMjN8u4k3eHzGETb1kRJfqbNSEugQkrskTHOJctl0VEbobY9JS3CBi0WxeALmoh4Rlaao2LllE85vPli2w3sGtia9rbsqJtFTW+KfcrutXJVJ+vGRqB9F31gQscNkZoo2uu5RjuGn5P83bu52nn9stikg9uuoIH/gZD8jIEgCnNWDAlmQCQH27BjaJuf6JNMPcvTQAHJDINmwJj7xCWd03k+dseT3vrFV6WTI7aEo9AAoEOhoPg/JCKNSWGJutW7pfkJh9SdUltpQIc+guU7YQaTJ8n8I+7i3YwIDAQAB';
    publicKeyPEM = "-----BEGIN PUBLIC KEY-----" + publicKeyPEM + "-----END PUBLIC KEY-----";
    const plainPassword = "1qaz2wsx";
    console.log("Found KEYUTIL:", typeof jsrsasign.KEYUTIL.getKey);

    const pubKeyObj = jsrsasign.KEYUTIL.getKey(publicKeyPEM);
    const encryptedHex = jsrsasign.KJUR.crypto.Cipher.encrypt(plainPassword, pubKeyObj);
    const encryptedBase64 = hexToBase64(encryptedHex);

    pm.environment.set("ENCRYPTED_PASSWORD", encryptedBase64);
    console.log("RSA 加密成功, 密文长度:", encryptedBase64.length);

    function hexToBase64(hexString) {
        const bytes = new Uint8Array(hexString.length / 2);
        for (let i = 0; i < hexString.length; i += 2) {
            bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);
        }
        if (typeof Buffer !== 'undefined') {
            return Buffer.from(bytes).toString('base64');
        }
        return btoa(String.fromCharCode.apply(null, bytes));
    };
    """

    # 2. 测试 crypto-js 与 Buffer
    cryptojs_script = """
    const CryptoJS = require('crypto-js');
    const md5Hex = CryptoJS.MD5('admin123').toString();
    const sha256Hex = CryptoJS.SHA256('SchemaPulse_Secret').toString();
    pm.variables.set('md5_val', md5Hex);
    pm.variables.set('sha256_val', sha256Hex);
    """

    pre_actions = [
        {"enabled": True, "type": "javascript", "value": user_script},
        {"enabled": True, "type": "javascript", "value": cryptojs_script}
    ]

    headers, params, body, path, vars_out = execute_pre_actions(
        pre_actions=pre_actions,
        headers={"Content-Type": "application/json"},
        params={},
        body='{"encrypted": "{{ENCRYPTED_PASSWORD}}", "md5": "{{md5_val}}", "sha256": "{{sha256_val}}"}',
        path="/api/auth"
    )

    assert vars_out.get("_script_error") is None, f"脚本执行错误: {vars_out.get('_script_error')}"
    assert "ENCRYPTED_PASSWORD" in vars_out, "ENCRYPTED_PASSWORD 未成功写入变量"
    assert vars_out["md5_val"] == "0192023a7bbd73250516f069df18b500"
    assert len(vars_out["sha256_val"]) == 64
    assert len(vars_out["ENCRYPTED_PASSWORD"]) > 50

    parsed_body = json.loads(body)
    assert parsed_body["encrypted"] == vars_out["ENCRYPTED_PASSWORD"]
    assert parsed_body["md5"] == "0192023a7bbd73250516f069df18b500"
    print(f"[OK] require('jsrsasign') RSA 加密与 require('crypto-js') MD5/SHA256 均执行成功！")
    print(f"     Body 成功插入 RSA 密文与签名: md5={parsed_body['md5']}, rsa_len={len(parsed_body['encrypted'])}")



def test_api_crud_and_persistence():
    print("\n==================================================")
    print("   3. 测试接口探针创建/读取/更新的持久化 (/api/apis)")
    print("==================================================")
    client = TestClient(app)
    with Session(engine) as session:
        machine = session.exec(select(MachineNode)).first()
        m_id = machine.id

    create_payload = {
        "machine_id": m_id,
        "name": "用户订单服务探针_测试",
        "http_path": "/get",
        "http_method": "GET",
        "expected_schema": {"type": "object"},
        "pre_actions": [
            {"enabled": True, "type": "set_variable", "key": "trace_seed", "value": "{{$uuid}}"},
            {"enabled": True, "type": "inject_header", "key": "X-Trace-Id", "value": "{{trace_seed}}"}
        ],
        "post_actions": [
            {"enabled": True, "name": "状态码200", "type": "assert_status_code", "operator": "equals", "target_value": "200"},
            {"enabled": True, "name": "响应小于2000ms", "type": "assert_latency", "operator": "less_than", "target_value": "2000"}
        ]
    }
    
    # 1. 创建接口
    c_res = client.post("/api/apis", json=create_payload)
    assert c_res.status_code == 200, f"创建失败: {c_res.text}"
    created_api = c_res.json()
    api_id = created_api["id"]
    assert len(created_api["pre_actions"]) == 2
    assert len(created_api["post_actions"]) == 2
    print(f"[OK] 接口创建成功, ID={api_id}, pre_actions={len(created_api['pre_actions'])}, post_actions={len(created_api['post_actions'])}")

    # 2. 读取列表验证回显
    l_res = client.get(f"/api/apis?machine_id={m_id}")
    assert l_res.status_code == 200
    apis = l_res.json()
    matched = next((a for a in apis if a["id"] == api_id), None)
    assert matched is not None
    assert matched["pre_actions"][0]["key"] == "trace_seed"
    assert matched["post_actions"][0]["target_value"] == "200"
    print(f"[OK] 列表读取回显一致: pre_actions[0].key={matched['pre_actions'][0]['key']}")

    # 3. 更新接口
    update_payload = dict(create_payload)
    update_payload["name"] = "用户订单服务探针_修改版"
    update_payload["post_actions"].append({
        "enabled": True,
        "name": "响应文本包含OK",
        "type": "assert_body_contains",
        "operator": "contains",
        "target_value": "OK"
    })
    u_res = client.put(f"/api/apis/{api_id}", json=update_payload)
    assert u_res.status_code == 200
    updated_api = u_res.json()
    assert updated_api["name"] == "用户订单服务探针_修改版"
    assert len(updated_api["post_actions"]) == 3
    print(f"[OK] 接口更新成功, post_actions 增至 {len(updated_api['post_actions'])} 条")

    # 4. 清理测试接口
    d_res = client.delete(f"/api/apis/{api_id}")
    assert d_res.status_code == 200
    print(f"[OK] 清理测试接口完成")


if __name__ == "__main__":
    test_action_engine_unit()
    test_api_test_run_with_actions()
    test_body_json_with_pre_action_parameters()
    test_crypto_libraries_require()
    test_api_crud_and_persistence()
    print("\n==================================================")
    print("🎉🎉 全部前置操作与后置操作测试 100% 通过！ 🎉🎉")
    print("==================================================")


