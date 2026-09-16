with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if "filteredEnvironments" in line or "handleDeleteEnv" in line:
        print(i, line.strip())
