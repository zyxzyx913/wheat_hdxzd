"""按 group_id 划分数据清单，生成无组间泄漏的 CSV 清单。"""

from __future__ import annotations

import argparse
from pathlib import Path

from wheat_phenotyping.data import read_manifest, split_by_group, split_counts, write_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="按植株/地块 group_id 拆分 train/validation/test")
    parser.add_argument("--manifest", type=Path, required=True, help="源 CSV；允许 split 列为空")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--validation-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = read_manifest(args.manifest, require_split=False)
    split_records = split_by_group(
        records,
        train_ratio=args.train_ratio,
        validation_ratio=args.validation_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )
    write_manifest(split_records, args.output, relative_to=args.output.parent)
    print(f"输出清单：{args.output}")
    print(f"样本划分计数：{split_counts(split_records)}")


if __name__ == "__main__":
    main()
