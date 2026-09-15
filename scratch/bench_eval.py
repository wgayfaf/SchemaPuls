import quickjs
import time

with open('scratch/jsrsasign_10.9.0.min.js', 'r', encoding='utf-8') as f:
    js_code = f.read()

ctx = quickjs.Context()
ctx.eval("var window = globalThis; var navigator = { userAgent: 'SchemaPulse' };")

t0 = time.perf_counter()
ctx.eval(js_code)
t1 = time.perf_counter()

print(f"Time to eval jsrsasign: {(t1 - t0)*1000:.2f} ms")
