"""导入浏览器下载的官方小麦价格周报，OCR 结果先进入人工复核队列。"""
from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "data/raw/economics/official_reports/inbox"
PROCESSED = ROOT / "data/raw/economics/official_reports/processed"
REJECTED = ROOT / "data/raw/economics/official_reports/rejected"
REVIEW = ROOT / "data/processed/economics/price_import_review.csv"
HTML = ROOT / "data/processed/economics/price_import_review.html"
FIELDS = ["date", "price_yuan_per_ton", "source_file", "source_url", "publication_date", "ocr_confidence", "verification_status", "review_notes"]


def detect_text(path: Path) -> tuple[str, float, str]:
    """尽量调用 pytesseract；缺少 OCR 引擎时返回待复核，不伪造文本。"""
    try:
        import pytesseract  # type: ignore
        from PIL import Image
        if path.suffix.lower() == ".pdf":
            return "", 0.0, "PDF OCR 需要安装独立解析器；未自动识别"
        text = pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng")
        return text, 0.0, "pytesseract 未提供可审计置信度；必须人工复核"
    except Exception as error:  # noqa: BLE001
        return "", 0.0, f"OCR 不可用: {error}"


def extract_candidates(text: str) -> tuple[str | None, float | None]:
    date_match = re.search(r"(20\d{2})[年\-/](\d{1,2})[月\-/](\d{1,2})", text)
    value_match = re.search(r"小麦.{0,80}?(\d{3,5}(?:\.\d+)?)\s*(元/吨|元\/吨|元/斤|元\/斤)", text, flags=re.S)
    if not value_match:
        return (f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}" if date_match else None), None
    value = float(value_match.group(1))
    if value_match.group(2).replace("/", "") == "元斤": value *= 2000
    return (f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}" if date_match else None), value


def main() -> None:
    for folder in (INBOX, PROCESSED, REJECTED, REVIEW.parent): folder.mkdir(parents=True, exist_ok=True)
    existing = {}
    if REVIEW.exists():
        with REVIEW.open(encoding="utf-8-sig", newline="") as stream:
            existing = {row.get("source_file"): row for row in csv.DictReader(stream)}
    for path in sorted(INBOX.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".pdf", ".jpg", ".jpeg", ".png"}: continue
        key = f"{path.name}:{sha256(path.read_bytes()).hexdigest()}"
        if key in existing: continue
        if path.suffix.lower() == ".csv":
            try:
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    imported = list(csv.DictReader(stream))
                for index, row in enumerate(imported):
                    existing[f"{key}:{index}"] = {"date": row.get("date", ""), "price_yuan_per_ton": row.get("price_yuan_per_ton", ""), "source_file": str(path.relative_to(ROOT)), "source_url": row.get("source_url", row.get("source", "")), "publication_date": row.get("publication_date", ""), "ocr_confidence": "1.0", "verification_status": "pending_manual_review", "review_notes": "CSV 导入，仍需核验全国平均小麦收购价口径"}
            except Exception as error:  # noqa: BLE001
                existing[key] = {"date": "", "price_yuan_per_ton": "", "source_file": str(path.relative_to(ROOT)), "source_url": "", "publication_date": "", "ocr_confidence": "0", "verification_status": "pending_manual_review", "review_notes": f"CSV 读取失败: {error}"}
        else:
            text, confidence, note = detect_text(path)
            observed_date, price = extract_candidates(text)
            existing[key] = {"date": observed_date or "", "price_yuan_per_ton": str(price or ""), "source_file": str(path.relative_to(ROOT)), "source_url": "", "publication_date": "", "ocr_confidence": str(confidence), "verification_status": "pending_manual_review", "review_notes": note}
        shutil.copy2(path, PROCESSED / path.name)
    with REVIEW.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader(); writer.writerows(existing.values())
    build_review_html(list(existing.values()))
    stats = {"review_records": len(existing), "confirmed_records": sum(row.get("verification_status") == "confirmed" for row in existing.values()), "main_series_records": 0, "new_confirmed_records": 0, "inbox_files": len([p for p in INBOX.iterdir() if p.is_file()])}
    (REVIEW.parent / "price_import_stats.json").write_text(__import__("json").dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"review_records={len(existing)} review_csv={REVIEW} review_html={HTML}")


def build_review_html(rows: list[dict[str, str]]) -> None:
    table = "".join(f"<tr><td>{r['source_file']}</td><td>{r['date']}</td><td>{r['price_yuan_per_ton']}</td><td>{r['verification_status']}</td><td>{r['review_notes']}</td></tr>" for r in rows)
    HTML.write_text("<meta charset='utf-8'><title>麦视通价格导入复核</title><h1>官方小麦价格导入复核</h1><p>只有人工确认后才能合并到正式价格 CSV。</p><table border='1'><tr><th>文件</th><th>日期</th><th>价格</th><th>状态</th><th>说明</th></tr>" + table + "</table>", encoding="utf-8")


if __name__ == "__main__": main()
