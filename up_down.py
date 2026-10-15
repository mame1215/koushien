from pathlib import Path
import pyhula

path = (
    Path(pyhula.__file__).parent
    / "system"
    / "taskcontroller.c"
)

lines = path.read_text(
    encoding="utf-8",
    errors="ignore"
).splitlines()

# Cファイルの行番号3630〜3750を表示
for i in range(3629, min(3750, len(lines))):
    print(f"{i + 1}: {lines[i]}")