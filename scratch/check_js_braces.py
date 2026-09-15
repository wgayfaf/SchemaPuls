with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# 统计括号匹配
stack = []
line = 1
col = 0
i = 0
in_quote = None
escaped = False

while i < len(text):
    c = text[i]
    if c == '\n':
        line += 1
        col = 0
    else:
        col += 1

    if in_quote:
        if escaped:
            escaped = False
        elif c == '\\':
            escaped = True
        elif c == in_quote:
            in_quote = None
    else:
        if c == '/' and i + 1 < len(text) and text[i+1] == '/':
            # 单行注释，跳到行尾
            nl = text.find('\n', i)
            if nl != -1:
                i = nl - 1
        elif c == '/' and i + 1 < len(text) and text[i+1] == '*':
            # 多行注释
            end_c = text.find('*/', i + 2)
            if end_c != -1:
                line += text.count('\n', i, end_c + 2)
                i = end_c + 1
        elif c in ['"', "'", '`']:
            in_quote = c
        elif c in '({[':
            stack.append((c, line, col))
        elif c in ')}]':
            if not stack:
                print(f"Extra closing {c} at line {line}:{col}")
            else:
                top, tline, tcol = stack.pop()
                pair = {'(': ')', '{': '}', '[': ']'}[top]
                if pair != c:
                    print(f"Mismatched closing {c} at line {line}:{col}, expected {pair}, opened {top} at line {tline}:{tcol}")
                    print("Remaining unclosed in stack:")
                    for u in stack[-5:]:
                        print(" ", u)
                    break
    i += 1

while stack:
    top, tline, tcol = stack.pop()
    print(f"Unclosed {top} from line {tline}:{tcol}")
