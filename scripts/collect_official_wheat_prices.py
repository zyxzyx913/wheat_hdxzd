"""采集国家粮食和物资储备局官方周报索引。

网络不可用、页面为图片或 OCR 不确定时只记录 pending_manual_review，绝不写入主预测序列。
"""
from __future__ import annotations

import csv
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/economics/official_weekly_reports"
AUDIT = ROOT / "data/processed/economics"
INDEX_URL = "https://www.lswz.gov.cn/html/zmhd/lysj/lsjg-scjc.shtml"


class ReportLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self._href = None; self._text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href"); self._text = []
    def handle_data(self, data):
        if self._href is not None: self._text.append(data.strip())
    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            text = " ".join(x for x in self._text if x)
            if "收购价格周报" in text: self.links.append((text, self._href))
            self._href = None


def fetch(url: str) -> bytes:
    return urlopen(Request(url, headers={"User-Agent": "MaishitongResearch/5.1"}), timeout=30).read()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True); AUDIT.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        html = fetch(INDEX_URL).decode("utf-8", errors="replace")
        parser = ReportLinkParser(); parser.feed(html)
        for title, href in parser.links:
            rows.append({"title": title, "source_url": href, "download_status": "discovered", "verification_status": "pending_manual_review", "extraction_method": "not_run", "error": ""})
    except (URLError, TimeoutError, OSError) as error:
        rows.append({"title": "official_index", "source_url": INDEX_URL, "download_status": "failed", "verification_status": "pending_manual_review", "extraction_method": "not_run", "error": str(error)})
    path = AUDIT / "price_source_manifest.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["title", "source_url", "download_status", "verification_status", "extraction_method", "error"])
        writer.writeheader(); writer.writerows(rows)
    print(f"discovered={len(rows)} manifest={path}")


if __name__ == "__main__": main()
