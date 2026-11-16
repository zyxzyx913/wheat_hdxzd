"""为独立 API 测试导入项目源码；产物只写 pytest 临时目录。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for directory in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
