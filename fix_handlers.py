
import os

file_path = '/opt/taiger/telegram_bot/handlers.py'

with open(file_path, 'r') as f:
    lines = f.readlines()

# Ranges to keep (1-based line numbers converted to 0-based indices)
# Range 1: 1 to 1717 (Index 0 to 1717)
part1 = lines[0:1717]

# Range 2: 3885 to 3910 (Index 3884 to 3910)
part2 = lines[3884:3910]

# Range 3: 4196 to End (Index 4195 to End)
part3 = lines[4195:]

new_content = "".join(part1 + part2 + part3)

with open(file_path, 'w') as f:
    f.write(new_content)

print(f"Fixed {file_path}. Original lines: {len(lines)}. New lines: {len(part1)+len(part2)+len(part3)}")
