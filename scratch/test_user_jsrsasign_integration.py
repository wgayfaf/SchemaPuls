import os
import sys
import json

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root_dir, "backend"))

from app.services.action_engine import execute_pre_actions

user_script = """
const jsrsasign = require('jsrsasign');

// 公钥
let publicKeyPEM = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy7YbsS0zH21A27PccrK99ee43Xf1hLlrmw3tO8U2DmO/mbc8mL/lMjN8u4k3eHzGETb1kRJfqbNSEugQkrskTHOJctl0VEbobY9JS3CBi0WxeALmoh4Rlaao2LllE85vPli2w3sGtia9rbsqJtFTW+KfcrutXJVJ+vGRqB9F31gQscNkZoo2uu5RjuGn5P83bu52nn9stikg9uuoIH/gZD8jIEgCnNWDAlmQCQH27BjaJuf6JNMPcvTQAHJDINmwJj7xCWd03k+dseT3vrFV6WTI7aEo9AAoEOhoPg/JCKNSWGJutW7pfkJh9SdUltpQIc+guU7YQaTJ8n8I+7i3YwIDAQAB';
publicKeyPEM = "-----BEGIN PUBLIC KEY-----"+ publicKeyPEM + "-----END PUBLIC KEY-----";
// 2. 获取明文密码（从环境变量或请求参数中获取）
const plainPassword = "1qaz2wsx";
console.log(jsrsasign.KEYUTIL.getKey)
// 4. 使用公钥加密密码

const pubKeyObj = jsrsasign.KEYUTIL.getKey(publicKeyPEM);
console.log('js import');
// RSA 加密（返回十六进制字符串）
const encryptedHex = jsrsasign.KJUR.crypto.Cipher.encrypt(plainPassword, pubKeyObj);
const encryptedBase64 = hexToBase64(encryptedHex);
console.log('js import');
// 5. 将加密后的密文保存到环境变量
pm.environment.set("ENCRYPTED_PASSWORD", JSON.stringify(encryptedBase64));

console.log("RSA 加密成功");
console.log("明文密码:", plainPassword);
console.log("加密密文:", encryptedHex);
// 十六进制转 Base64
function hexToBase64(hexString) {
    const bytes = new Uint8Array(hexString.length / 2);
    for (let i = 0; i < hexString.length; i += 2) {
        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);
    }
    // Node.js 环境
    if (typeof Buffer !== 'undefined') {
        return Buffer.from(bytes).toString('base64');
    }
    // 浏览器环境
    return btoa(String.fromCharCode.apply(null, bytes));
};
"""

pre_actions = [
    {"enabled": True, "type": "javascript", "value": user_script}
]

headers, params, body, path, vars_out = execute_pre_actions(
    pre_actions=pre_actions,
    headers={"Content-Type": "application/json"},
    params={},
    body='{"password": {{ENCRYPTED_PASSWORD}}}',
    path="/api/login"
)

print("Script Error?:", vars_out.get("_script_error"))
print("ENCRYPTED_PASSWORD in variables?:", "ENCRYPTED_PASSWORD" in vars_out)
print("Rendered body:", body)
print("Logs count:", len(vars_out.get("_console_logs", [])))
for log in vars_out.get("_console_logs", []):
    print("  LOG:", log)

assert vars_out.get("_script_error") is None, f"Script error: {vars_out.get('_script_error')}"
assert "ENCRYPTED_PASSWORD" in vars_out, "ENCRYPTED_PASSWORD not found"
assert '"password":' in body
print("\n>>> ALL CHECKS PASSED PERFECTLY! <<<")
