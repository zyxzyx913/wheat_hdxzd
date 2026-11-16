"""对运行中的服务做 EWS train 单图冒烟；不计算精度、不调参。"""

import argparse
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path

import httpx
from PIL import Image

from wheat_phenotyping.app.inference import predict_visible_mask
from wheat_phenotyping.data import load_rgb_image

from backend.app.config import PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "reports/web_exg_smoke_test.json")
    args = parser.parse_args()
    manifest = PROJECT_ROOT / "data/processed/ews/manifest.csv"
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        record = next(row for row in csv.DictReader(stream) if row["split"] == "train")
    image_path = (manifest.parent / record["image_path"]).resolve()
    uploaded_bytes = image_path.read_bytes()
    with httpx.Client(base_url=args.base_url, trust_env=False, timeout=120) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        response = client.post("/api/image/analyze", files={"file": (image_path.name, uploaded_bytes, "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg")})
        response.raise_for_status()
        result = response.json()
        asset_sizes = {}
        mask_pixels = b""
        for field in ("original_url", "mask_url", "overlay_url"):
            asset = client.get(result[field])
            asset.raise_for_status()
            with Image.open(BytesIO(asset.content)) as opened:
                opened.load()
                assert opened.size == (result["width"], result["height"])
                asset_sizes[field] = list(opened.size)
                if field == "mask_url":
                    assert opened.mode == "L"
                    mask_pixels = opened.tobytes()
        assert set(mask_pixels) <= {0, 255}
        foreground = mask_pixels.count(255)
        assert foreground == result["vegetation_pixel_count"]
        assert len(mask_pixels) == result["total_valid_pixels"]
        assert foreground / len(mask_pixels) == result["vegetation_ratio"]
        expected, _ = predict_visible_mask(load_rgb_image(image_path), "ExG", parameters=result["parameters"])
        assert expected.pixels == mask_pixels
        directory = PROJECT_ROOT / "var/web/analyses" / result["task_id"]
        raw_path = directory / ("uploaded_original" + (".png" if image_path.suffix.lower() == ".png" else ".jpg"))
        assert raw_path.read_bytes() == uploaded_bytes
        assert (directory / "record.json").is_file()
        report = {
            "verification_type": "real EWS train image HTTP smoke test; NOT model accuracy evaluation",
            "source_sample_id": record["sample_id"], "source_split": record["split"],
            "dataset_name": record["dataset_name"], "dataset_version": record["dataset_version"],
            "source_image": str(image_path), "input_sha256": hashlib.sha256(uploaded_bytes).hexdigest(),
            "base_url": args.base_url, "health_status": health.status_code,
            "analyze_status": response.status_code, "result": result,
            "asset_dimensions": asset_sizes, "mask_pixel_count_verified": foreground,
            "direct_exg_mask_equal": True, "uploaded_bytes_unchanged": True,
            "artifact_directory": str(directory),
            "warning": "只验证接口、文件与计算一致性；未使用人工标注评价，未更新 EWS 实验成绩。",
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
