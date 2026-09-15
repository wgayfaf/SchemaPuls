from bs4 import BeautifulSoup
import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

def check_expr(expr, tag_info):
    if not expr or not expr.strip():
        return
    # check paren balance
    if expr.count('(') != expr.count(')'):
        print(f"Paren mismatch in {tag_info}: {expr}")
    # check dangling parens
    if re.search(r'\([^\)]*\)\)', expr):
        print(f"Double closing paren in {tag_info}: {expr}")

for tag in soup.find_all(True):
    for attr, val in tag.attrs.items():
        if attr.startswith('@') or attr.startswith('v-on:') or attr.startswith(':') or attr.startswith('v-bind:') or attr.startswith('v-if') or attr.startswith('v-show'):
            check_expr(str(val), f"<{tag.name} {attr}>")
