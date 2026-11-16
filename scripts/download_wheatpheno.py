"""从官方 Zenodo 断点续传 WheatPheno，并在完成后校验 MD5。"""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://zenodo.org/records/8115362/files/WheatPheno_part_1.zip?download=1"
EXPECTED_SIZE = 8_881_621_279
EXPECTED_MD5 = "44ad918c0fd9c1915901bc6665a8e0be"
DEST = Path(__file__).resolve().parents[1] / "data/raw/wheatpheno/WheatPheno_part_1.zip"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    existing = DEST.stat().st_size if DEST.exists() else 0
    headers = {"Range": f"bytes={existing}-"} if existing else {}
    request = Request(URL, headers=headers)
    with urlopen(request, timeout=60) as response, DEST.open("ab" if existing else "wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            print(f"downloaded={output.tell()} bytes", flush=True)
    if DEST.stat().st_size != EXPECTED_SIZE:
        raise RuntimeError(f"文件大小不匹配: {DEST.stat().st_size} != {EXPECTED_SIZE}")
    digest = hashlib.md5()
    with DEST.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != EXPECTED_MD5:
        raise RuntimeError(f"MD5 不匹配: {digest.hexdigest()} != {EXPECTED_MD5}")
    print("下载完成且 MD5 校验通过")


if __name__ == "__main__":
    main()
