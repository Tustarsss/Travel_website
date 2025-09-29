# Script to see the structure around the problem area
with open("app/services/data_generation/generator.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Print lines around where the conditional structure should be
for i in range(224, min(len(lines), 360)):
    line = lines[i]
    if i in [224, 270, 347, 354]:  # Key structural lines
        print(f"{i+1:3d}: {repr(line)}")
    elif "counters.region +=" in line or "if osm_data:" in line or "else:" in line:
        print(f"{i+1:3d}: {repr(line)}")
    elif "# Process graph edges" in line:
        print(f"{i+1:3d}: {repr(line)}")