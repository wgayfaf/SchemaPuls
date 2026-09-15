import quickjs
import urllib.request
import os

with open('scratch/jsrsasign_10.9.0.min.js', 'rb') as f:
    content = f.read()

print(f"Loaded jsrsasign 10.9.0 ({len(content)} bytes)")

ctx = quickjs.Context()

# Evaluate polyfills first: window, navigator, Buffer, etc.
polyfill = """
var window = globalThis;
var navigator = { userAgent: "SchemaPulse/QuickJS" };
var _b64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
function btoa(input) {
    var str = String(input);
    var output = '';
    for (var block = 0, charCode, i = 0, map = _b64chars;
         str.charAt(i | 0) || (map = '=', i % 1);
         output += map.charAt(63 & block >> 8 - i % 1 * 8)) {
        charCode = str.charCodeAt(i += 3/4);
        if (charCode > 0xFF) {
            throw new Error("'btoa' failed: The string to be encoded contains characters outside of the Latin1 range.");
        }
        block = block << 8 | charCode;
    }
    return output;
}
"""

ctx.eval(polyfill)

try:
    ctx.eval(content.decode('utf-8'))
    print("jsrsasign evaluated successfully in quickjs!")
except Exception as e:
    print("Failed to evaluate jsrsasign:", e)

# Setup require('jsrsasign') and Buffer polyfill
setup_require = """
var Buffer = {
    from: function(data, enc) {
        var bytes;
        if (data instanceof Uint8Array || Array.isArray(data)) {
            bytes = data;
        } else if (typeof data === 'string') {
            if (enc === 'hex') {
                bytes = [];
                for (var i = 0; i < data.length; i += 2) bytes.push(parseInt(data.substr(i, 2), 16));
            } else if (enc === 'base64') {
                var bin = atob(data);
                bytes = [];
                for (var i = 0; i < bin.length; i++) bytes.push(bin.charCodeAt(i));
            } else {
                bytes = [];
                for (var i = 0; i < data.length; i++) bytes.push(data.charCodeAt(i));
            }
        } else {
            bytes = [];
        }
        return {
            toString: function(outEnc) {
                if (outEnc === 'base64') {
                    var bin = '';
                    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
                    return btoa(bin);
                }
                if (outEnc === 'hex') {
                    var hex = '';
                    for (var i = 0; i < bytes.length; i++) {
                        var h = (bytes[i] & 0xFF).toString(16);
                        hex += (h.length === 1 ? '0' : '') + h;
                    }
                    return hex;
                }
                var s = '';
                for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
                return s;
            }
        };
    }
};

var jsrsasignObj = {
    KEYUTIL: typeof KEYUTIL !== 'undefined' ? KEYUTIL : {},
    KJUR: typeof KJUR !== 'undefined' ? KJUR : {},
    CryptoJS: typeof CryptoJS !== 'undefined' ? CryptoJS : {},
    ASN1HEX: typeof ASN1HEX !== 'undefined' ? ASN1HEX : {},
    X509: typeof X509 !== 'undefined' ? X509 : {}
};

function require(moduleName) {
    var name = String(moduleName).toLowerCase().trim();
    if (name === 'jsrsasign') {
        return jsrsasignObj;
    }
    if (name === 'crypto-js') {
        return typeof CryptoJS !== 'undefined' ? CryptoJS : {};
    }
    if (name === 'buffer') {
        return { Buffer: Buffer };
    }
    throw new Error("Cannot find module '" + moduleName + "'");
}
"""
ctx.eval(setup_require)



test_user_code = """
var logMsg = [];
var console = {
    log: function() { logMsg.push(Array.from(arguments).join(' ')); }
};
var env = {};
var pm = {
    environment: {
        set: function(k, v) { env[k] = v; },
        get: function(k) { return env[k]; }
    }
};

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
    var bin = '';
    for (var i = 0; i < bytes.length; i++) {
        bin += String.fromCharCode(bytes[i]);
    }
    return btoa(bin);
};

JSON.stringify({ logs: logMsg, env: env });
"""

res_json = ctx.eval(test_user_code)
print("EXECUTION RESULT:")
import json
print(json.dumps(json.loads(res_json), indent=2, ensure_ascii=False))






