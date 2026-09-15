import quickjs
import json

ctx = quickjs.Context()
try:
    ctx.eval("require('jsrsasign')")
except Exception as e:
    print("Error:", repr(e))
