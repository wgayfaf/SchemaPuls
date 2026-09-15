with open('frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    if '@click' in line or ':content' in line:
        # check quotes and parens
        if line.count('(') != line.count(')'):
            print(f"Line {idx} paren mismatch: {line.strip()}")
