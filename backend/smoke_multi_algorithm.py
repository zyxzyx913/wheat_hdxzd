"""同一张真实 EWS train 图像的四算法 HTTP 检查，不调参、不计算精度。"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path

import httpx
from PIL import Image

from backend.app.config import PROJECT_ROOT, SUPPORTED_ALGORITHMS
from wheat_phenotyping.app.inference import predict_visible_mask
from wheat_phenotyping.data import load_rgb_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "reports/web_multi_algorithm_smoke.json")
    args = parser.parse_args()
    manifest = PROJECT_ROOT / "data/processed/ews/manifest.csv"
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        sample = next(row for row in csv.DictReader(stream) if row["split"] == "train")
    image_path = (manifest.parent / sample["image_path"]).resolve()
    raw = image_path.read_bytes()
    rgb = load_rgb_image(image_path)
    source_hash = hashlib.sha256(raw).hexdigest()
    results = []
    canonical_hashes = set()
    with httpx.Client(base_url=args.base_url, trust_env=False, timeout=120) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        assert health.json()["available_algorithms"] == list(SUPPORTED_ALGORITHMS)
        for algorithm in SUPPORTED_ALGORITHMS:
            response = client.post("/api/image/analyze", files={"file": (image_path.name, raw, "image/png")}, data={"algorithm": algorithm})
            response.raise_for_status()
            result = response.json()
            assert result["algorithm"] == algorithm
            assert result["input_sha256"] == source_hash
            assert (result["width"], result["height"]) == (rgb.width, rgb.height)
            expected, metadata = predict_visible_mask(rgb, algorithm, parameters=result["parameters"])
            for key in ("original_url", "mask_url", "overlay_url"):
                asset = client.get(result[key])
                asset.raise_for_status()
                with Image.open(BytesIO(asset.content)) as opened:
                    opened.load()
                    assert opened.size == (rgb.width, rgb.height)
                    if key == "original_url":
                        canonical_hashes.add(hashlib.sha256(opened.tobytes()).hexdigest())
                    if key == "mask_url":
                        assert opened.mode == "L"
                        pixels = opened.tobytes()
                        assert set(pixels) <= {0, 255}
                        assert pixels == expected.pixels
                        assert result["vegetation_pixel_count"] == pixels.count(255)
                        assert result["total_valid_pixels"] == len(pixels)
                        assert result["vegetation_ratio"] == pixels.count(255) / len(pixels)
            assert result["algorithm_metadata"] == metadata
            directory = PROJECT_ROOT / "var/web/analyses" / result["task_id"]
            assert (directory / "uploaded_original.png").read_bytes() == raw
            saved = json.loads((directory / "record.json").read_text(encoding="utf-8"))
            assert saved["algorithm"] == algorithm and saved["input_sha256"] == source_hash
            results.append({**result, "http_status": response.status_code, "mask_count_verified": True,
                            "direct_predictor_mask_equal": True, "all_assets_decodable": True,
                            "artifact_directory": str(directory)})
    assert len(canonical_hashes) == 1
    assert len({row["task_id"] for row in results}) == 4
    report = {
        "verification_type": "real EWS train image four-algorithm HTTP consistency check; NOT accuracy evaluation",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "base_url": args.base_url,
        "source_sample_id": sample["sample_id"], "source_split": "train",
        "dataset_name": sample["dataset_name"], "dataset_version": sample["dataset_version"],
        "source_image": str(image_path), "input_sha256": source_hash,
        "same_canonical_rgb": True, "results": results,
        "warning": "未使用人工标注计算精度；面积比例差异不是算法准确率；未修改 EWS 成绩。",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
