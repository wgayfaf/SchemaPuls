import sys
sys.path.insert(0, 'backend')
from app.services.action_engine import execute_pre_actions, execute_post_actions
from app.services.postman_importer import parse_postman_package

raw_json = '''{
    "info": {
        "name": "table",
        "description": "",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "auth",
            "description": "",
            "item": [
                {
                    "name": "login",
                    "description": "",
                    "item": [
                        {
                            "name": "邮箱登录",
                            "description": "",
                            "event": [
                                {
                                    "listen": "prerequest",
                                    "script": {
                                        "exec": [
                                            "const jsrsasign = require('jsrsasign');\\r",
                                            "\\r",
                                            "// 公钥\\r",
                                            "let publicKeyPEM = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy7YbsS0zH21A27PccrK99ee43Xf1hLlrmw3tO8U2DmO/mbc8mL/lMjN8u4k3eHzGETb1kRJfqbNSEugQkrskTHOJctl0VEbobY9JS3CBi0WxeALmoh4Rlaao2LllE85vPli2w3sGtia9rbsqJtFTW+KfcrutXJVJ+vGRqB9F31gQscNkZoo2uu5RjuGn5P83bu52nn9stikg9uuoIH/gZD8jIEgCnNWDAlmQCQH27BjaJuf6JNMPcvTQAHJDINmwJj7xCWd03k+dseT3vrFV6WTI7aEo9AAoEOhoPg/JCKNSWGJutW7pfkJh9SdUltpQIc+guU7YQaTJ8n8I+7i3YwIDAQAB';\\r",
                                            "publicKeyPEM = \\"-----BEGIN PUBLIC KEY-----\\"+ publicKeyPEM + \\"-----END PUBLIC KEY-----\\";\\r",
                                            "// 2. 获取明文密码（从环境变量或请求参数中获取）\\r",
                                            "const plainPassword = \\"1qaz2wsx\\";\\r",
                                            "console.log(jsrsasign.KEYUTIL.getKey)\\r",
                                            "// 4. 使用公钥加密密码\\r",
                                            "\\r",
                                            "const pubKeyObj = jsrsasign.KEYUTIL.getKey(publicKeyPEM);\\r",
                                            "console.log('js import');\\r",
                                            "// RSA 加密（返回十六进制字符串）\\r",
                                            "const encryptedHex = jsrsasign.KJUR.crypto.Cipher.encrypt(plainPassword, pubKeyObj);\\r",
                                            "const encryptedBase64 = hexToBase64(encryptedHex);\\r",
                                            "console.log('js import');\\r",
                                            "// 5. 将加密后的密文保存到环境变量\\r",
                                            "pm.environment.set(\\"ENCRYPTED_PASSWORD\\", JSON.stringify(encryptedBase64));\\r",
                                            "\\r",
                                            "console.log(\\"RSA 加密成功\\");\\r",
                                            "console.log(\\"明文密码:\\", plainPassword);\\r",
                                            "console.log(\\"加密密文:\\", encryptedHex);\\r",
                                            "// 十六进制转 Base64\\r",
                                            "function hexToBase64(hexString) {\\r",
                                            "    const bytes = new Uint8Array(hexString.length / 2);\\r",
                                            "    for (let i = 0; i < hexString.length; i += 2) {\\r",
                                            "        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);\\r",
                                            "    }\\r",
                                            "    // Node.js 环境\\r",
                                            "    if (typeof Buffer !== 'undefined') {\\r",
                                            "        return Buffer.from(bytes).toString('base64');\\r",
                                            "    }\\r",
                                            "    // 浏览器环境\\r",
                                            "    return btoa(String.fromCharCode.apply(null, bytes));\\r",
                                            "};\\r",
                                            "    \\r",
                                            "\\r",
                                            "",
                                            "const jsrsasign = require('jsrsasign');\\r",
                                            "\\r",
                                            "// 公钥\\r",
                                            "let publicKeyPEM = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy7YbsS0zH21A27PccrK99ee43Xf1hLlrmw3tO8U2DmO/mbc8mL/lMjN8u4k3eHzGETb1kRJfqbNSEugQkrskTHOJctl0VEbobY9JS3CBi0WxeALmoh4Rlaao2LllE85vPli2w3sGtia9rbsqJtFTW+KfcrutXJVJ+vGRqB9F31gQscNkZoo2uu5RjuGn5P83bu52nn9stikg9uuoIH/gZD8jIEgCnNWDAlmQCQH27BjaJuf6JNMPcvTQAHJDINmwJj7xCWd03k+dseT3vrFV6WTI7aEo9AAoEOhoPg/JCKNSWGJutW7pfkJh9SdUltpQIc+guU7YQaTJ8n8I+7i3YwIDAQAB';\\r",
                                            "publicKeyPEM = \\"-----BEGIN PUBLIC KEY-----\\"+ publicKeyPEM + \\"-----END PUBLIC KEY-----\\";\\r",
                                            "// 2. 获取明文密码（从环境变量或请求参数中获取）\\r",
                                            "const plainPassword = \\"admin123\\";\\r",
                                            "console.log(jsrsasign.KEYUTIL.getKey)\\r",
                                            "// 4. 使用公钥加密密码\\r",
                                            "\\r",
                                            "const pubKeyObj = jsrsasign.KEYUTIL.getKey(publicKeyPEM);\\r",
                                            "console.log('js import');\\r",
                                            "// RSA 加密（返回十六进制字符串）\\r",
                                            "const encryptedHex = jsrsasign.KJUR.crypto.Cipher.encrypt(plainPassword, pubKeyObj);\\r",
                                            "const encryptedBase64 = hexToBase64(encryptedHex);\\r",
                                            "console.log('js import');\\r",
                                            "// 5. 将加密后的密文保存到环境变量\\r",
                                            "pm.environment.set(\\"ENCRYPTED_PASSWORD\\", JSON.stringify(encryptedBase64));\\r",
                                            "\\r",
                                            "console.log(\\"RSA 加密成功\\");\\r",
                                            "console.log(\\"明文密码:\\", plainPassword);\\r",
                                            "console.log(\\"加密密文:\\", encryptedHex);\\r",
                                            "// 十六进制转 Base64\\r",
                                            "function hexToBase64(hexString) {\\r",
                                            "    const bytes = new Uint8Array(hexString.length / 2);\\r",
                                            "    for (let i = 0; i < hexString.length; i += 2) {\\r",
                                            "        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);\\r",
                                            "    }\\r",
                                            "    // Node.js 环境\\r",
                                            "    if (typeof Buffer !== 'undefined') {\\r",
                                            "        return Buffer.from(bytes).toString('base64');\\r",
                                            "    }\\r",
                                            "    // 浏览器环境\\r",
                                            "    return btoa(String.fromCharCode.apply(null, bytes));\\r",
                                            "};\\r",
                                            "    \\r",
                                            "\\r",
                                            "",
                                            "const jsrsasign = require('jsrsasign');\\r",
                                            "\\r",
                                            "// 公钥\\r",
                                            "let publicKeyPEM = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy7YbsS0zH21A27PccrK99ee43Xf1hLlrmw3tO8U2DmO/mbc8mL/lMjN8u4k3eHzGETb1kRJfqbNSEugQkrskTHOJctl0VEbobY9JS3CBi0WxeALmoh4Rlaao2LllE85vPli2w3sGtia9rbsqJtFTW+KfcrutXJVJ+vGRqB9F31gQscNkZoo2uu5RjuGn5P83bu52nn9stikg9uuoIH/gZD8jIEgCnNWDAlmQCQH27BjaJuf6JNMPcvTQAHJDINmwJj7xCWd03k+dseT3vrFV6WTI7aEo9AAoEOhoPg/JCKNSWGJutW7pfkJh9SdUltpQIc+guU7YQaTJ8n8I+7i3YwIDAQAB';\\r",
                                            "publicKeyPEM = \\"-----BEGIN PUBLIC KEY-----\\"+ publicKeyPEM + \\"-----END PUBLIC KEY-----\\";\\r",
                                            "// 2. 获取明文密码（从环境变量或请求参数中获取）\\r",
                                            "const plainPassword = \\"Code+183296\\";\\r",
                                            "console.log(jsrsasign.KEYUTIL.getKey)\\r",
                                            "// 4. 使用公钥加密密码\\r",
                                            "\\r",
                                            "const pubKeyObj = jsrsasign.KEYUTIL.getKey(publicKeyPEM);\\r",
                                            "console.log('js import');\\r",
                                            "// RSA 加密（返回十六进制字符串）\\r",
                                            "const encryptedHex = jsrsasign.KJUR.crypto.Cipher.encrypt(plainPassword, pubKeyObj);\\r",
                                            "const encryptedBase64 = hexToBase64(encryptedHex);\\r",
                                            "console.log('js import');\\r",
                                            "// 5. 将加密后的密文保存到环境变量\\r",
                                            "pm.environment.set(\\"ENCRYPTED_PASSWORD\\", JSON.stringify(encryptedBase64));\\r",
                                            "\\r",
                                            "console.log(\\"RSA 加密成功\\");\\r",
                                            "console.log(\\"明文密码:\\", plainPassword);\\r",
                                            "console.log(\\"加密密文:\\", encryptedHex);\\r",
                                            "// 十六进制转 Base64\\r",
                                            "function hexToBase64(hexString) {\\r",
                                            "    const bytes = new Uint8Array(hexString.length / 2);\\r",
                                            "    for (let i = 0; i < hexString.length; i += 2) {\\r",
                                            "        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);\\r",
                                            "    }\\r",
                                            "    // Node.js 环境\\r",
                                            "    if (typeof Buffer !== 'undefined') {\\r",
                                            "        return Buffer.from(bytes).toString('base64');\\r",
                                            "    }\\r",
                                            "    // 浏览器环境\\r",
                                            "    return btoa(String.fromCharCode.apply(null, bytes));\\r",
                                            "};\\r",
                                            "    \\r",
                                            "\\r",
                                            ""
                                        ],
                                        "type": "text/javascript",
                                        "packages": {}
                                    }
                                },
                                {
                                    "listen": "test",
                                    "script": {
                                        "exec": [
                                            "const res = pm.response.json();",
                                            "",
                                            "// 检查请求是否成功",
                                            "if (res.code === 0 && res.data && res.data.accessToken) {",
                                            "    // 将 accessToken 写入当前环境变量",
                                            "    pm.environment.set(\\"token\\", res.data.accessToken);",
                                            "    console.log(\\"Token 已保存:\\", res.data.accessToken);",
                                            "} else {",
                                            "    console.log(\\"登录失败或未获取到 token\\");",
                                            "}"
                                        ],
                                        "type": "text/javascript",
                                        "packages": {}
                                    }
                                }
                            ],
                            "auth": {},
                            "request": {
                                "auth": {
                                    "type": "noauth",
                                    "noauth": []
                                },
                                "method": "POST",
                                "body": {
                                    "mode": "raw",
                                    "raw": "{\\r\\n  \\"email\\": \\"wuyu@chubbycenter.com\\",\\r\\n  \\"password\\": {{ENCRYPTED_PASSWORD}}\\r\\n}",
                                    "options": {
                                        "raw": {
                                            "language": "json"
                                        }
                                    }
                                },
                                "header": [],
                                "url": {
                                    "raw": "{{baseUrl}}/api/auth/acc/email/login",
                                    "path": [
                                        "api",
                                        "auth",
                                        "acc",
                                        "email",
                                        "login"
                                    ],
                                    "host": [
                                        "{{baseUrl}}"
                                    ],
                                    "query": [],
                                    "variable": []
                                }
                            },
                            "response": []
                        }
                    ]
                }
            ]
        }
    ]
}'''

parsed = parse_postman_package(raw_json.encode('utf-8'), "login.json")
api = parsed["apis"][0]

print("=== 1. 执行 Pre-actions ===")
final_headers, final_params, final_body, final_path, variables, pre_updated_env = execute_pre_actions(
    pre_actions=api["pre_actions"],
    headers={},
    params={},
    body=api["http_body"],
    path=api["http_path"],
    environment_variables={}
)
print("Variables keys:", list(variables.keys()))
print("Pre updated env keys:", list(pre_updated_env.keys()))
print("Script error in variables:", variables.get("_script_error"))
print("Final Body:", final_body)

print("\n=== 2. 模拟响应并执行 Post-actions ===")
mock_resp = {
    "code": 0,
    "msg": "success",
    "data": {
        "accessToken": "ey_mocked_access_token_1234567890",
        "userId": "usr_9988"
    }
}
all_passed, assertions_result, extracted_vars, post_updated_env = execute_post_actions(
    post_actions=api["post_actions"],
    status_code=200,
    latency_ms=120,
    response_data=mock_resp,
    response_text=str(mock_resp),
    environment_variables=pre_updated_env
)
print("Post assertions count:", len(assertions_result))
print("Post assertions:", assertions_result)
print("Post updated env:", post_updated_env)
