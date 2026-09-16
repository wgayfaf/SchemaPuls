import quickjs, json

ctx = quickjs.Context()
ctx.eval('var beforeKeys = Object.keys(globalThis);')
ctx.eval('token = "hello_world"; var another = 456;')
res = ctx.eval('''
JSON.stringify(Object.keys(globalThis).filter(function(k) {
    return beforeKeys.indexOf(k) === -1;
}))
''')
print('Newly attached globals:', res)
