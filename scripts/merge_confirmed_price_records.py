"""仅将 verification_status=confirmed 的人工复核记录合并到主价格序列。"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "data/processed/economics/price_import_review.csv"
MAIN = ROOT / "data/raw/economics/national_wheat_price.csv"


def main() -> None:
    existing = {}
    with MAIN.open(encoding="utf-8-sig", newline="") as stream:
        existing = {row["date"]: row for row in csv.DictReader(stream)}
    added = 0
    if REVIEW.exists():
        with REVIEW.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("verification_status") != "confirmed" or not row.get("date") or not row.get("price_yuan_per_ton"):
                    continue
                date.fromisoformat(row["date"]); float(row["price_yuan_per_ton"])
                if row["date"] not in existing:
                    existing[row["date"]] = {"date": row["date"], "price_yuan_per_ton": row["price_yuan_per_ton"], "source": row.get("source_url") or row.get("source_file", "")}
                    added += 1
    with MAIN.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["date", "price_yuan_per_ton", "source"]); writer.writeheader(); writer.writerows(existing[key] for key in sorted(existing))
    print(f"added={added} total={len(existing)}")


if __name__ == "__main__": main()
