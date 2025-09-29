# Check specific lines to identify indentation issues
with open("app/services/data_generation/generator.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Print lines around 272 (0-indexed so 271)
for i in range(max(0, 270), min(len(lines), 276)):
    print(f"{i+1}: {repr(lines[i])}")