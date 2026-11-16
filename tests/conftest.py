"""为 src 布局项目配置测试导入路径。"""

import sys
from pathlib import Path


# 测试直接从源码目录导入包，用户无需先安装项目本身。
PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))
