"""校验后的 WheatPheno ZIP 安全解压与轻量图片清单生成器。"""
from __future__ import annotations

import csv
from hashlib import md5
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/wheatpheno/WheatPheno_part_1.zip"
DEST = ROOT / "data/raw/wheatpheno/extracted"
EXPECTED_SIZE = 8_881_621_279
EXPECTED_MD5 = "44ad918c0fd9c1915901bc6665a8e0be"


def verify_archive() -> None:
    if not ARCHIVE.is_file():
        raise FileNotFoundError(f"未找到官方 ZIP: {ARCHIVE}")
    if ARCHIVE.stat().st_size != EXPECTED_SIZE:
        raise RuntimeError("文件大小与官方记录不一致，禁止解压")
    digest = md5()
    with ARCHIVE.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != EXPECTED_MD5:
        raise RuntimeError("MD5 与官方记录不一致，禁止解压")


def main() -> None:
    verify_archive()
    DEST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = archive.infolist()
        root = DEST.resolve()
        for member in members:
            target = (DEST / member.filename).resolve()
            if not target.is_relative_to(root):
                raise RuntimeError(f"检测到路径穿越: {member.filename}")
        for index, member in enumerate(members, 1):
            target = DEST / member.filename
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as output:
                    output.write(source.read())
            if index % 1000 == 0:
                print(f"extracted={index}/{len(members)}", flush=True)
    print(f"解压完成: {len(members)} 个 ZIP 成员")


if __name__ == "__main__":
    main()
