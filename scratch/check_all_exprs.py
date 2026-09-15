from bs4 import BeautifulSoup
import quickjs

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
ctx = quickjs.Context()

for tag in soup.find_all(True):
    for attr, val in tag.attrs.items():
        if not isinstance(val, str):
            continue
        expr = val.strip()
        if attr.startswith('@') or attr.startswith('v-on:'):
            # Test event handler: function($event) { <expr> }
            test_js = f"(function($event) {{ {expr} }})"
            try:
                ctx.eval(test_js)
            except Exception as e:
                print(f"EVENT HANDLER ERROR in <{tag.name} {attr}=\"{expr}\">: {e}")
        elif attr.startswith(':') or attr.startswith('v-bind:') or attr in ['v-if', 'v-else-if', 'v-show']:
            # Test expression: (function() { return (<expr>); })
            test_js = f"(function() {{ return ({expr}); }})"
            try:
                ctx.eval(test_js)
            except Exception as e:
                print(f"BINDING ERROR in <{tag.name} {attr}=\"{expr}\">: {e}")
