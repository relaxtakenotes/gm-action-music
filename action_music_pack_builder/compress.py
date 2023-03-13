import subprocess
import os
from pathlib import Path

for path in Path('build\\exe.win-amd64-3.11\\').rglob('*.dll'):
	print(f"upx -9 \"{os.path.abspath(path)}\"")
	subprocess.Popen(f"upx -9 \"{os.path.abspath(path)}\"")
