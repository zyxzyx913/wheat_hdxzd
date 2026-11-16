"""数据清单、图像/标注读取和 group 划分测试。"""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wheat_phenotyping.data import (
    DatasetRecord,
    load_binary_mask,
    load_rgb_image,
    load_sample_images,
    read_manifest,
    split_by_group,
    split_counts,
    validate_records,
    write_manifest,
)


class ImageLoadingTest(unittest.TestCase):
    """验证公开常见图像格式、标签二值性和尺寸一致性。"""

    def test_loads_png_jpeg_and_existing_ppm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rgb = Image.new("RGB", (3, 2), (25, 180, 35))
            png = root / "plant.png"
            jpg = root / "plant.jpg"
            rgb.save(png)
            rgb.save(jpg)
            ppm = root / "plant.ppm"
            ppm.write_bytes(b"P6\n3 2\n255\n" + bytes((25, 180, 35) * 6))
            for path in (png, jpg, ppm):
                image = load_rgb_image(path)
                self.assertEqual((image.width, image.height), (3, 2))
                self.assertEqual(len(image.pixels), 18)

    def test_loads_binary_png_mask_and_rejects_nonbinary_gray(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mask_path = root / "mask.png"
            mask = Image.new("L", (2, 1))
            mask.putdata([0, 255])
            mask.save(mask_path)
            self.assertEqual(load_binary_mask(mask_path).pixels, bytes((0, 255)))
            invalid_path = root / "gray.png"
            invalid = Image.new("L", (2, 1))
            invalid.putdata([0, 120])
            invalid.save(invalid_path)
            with self.assertRaises(ValueError):
                load_binary_mask(invalid_path)

    def test_image_and_annotation_size_mismatch_is_not_resized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "image.png"
            mask = root / "mask.png"
            Image.new("RGB", (4, 3), "green").save(image)
            Image.new("L", (3, 3), 0).save(mask)
            with self.assertRaisesRegex(ValueError, "不会自动缩放"):
                load_sample_images(image, mask)


class ManifestAndSplitTest(unittest.TestCase):
    """验证字段、来源、文件和 group 隔离，以及确定性分组划分。"""

    def _records(self, root: Path, groups: int = 9) -> list[DatasetRecord]:
        records = []
        for group in range(groups):
            for view in range(2):
                image = root / f"g{group}_v{view}.ppm"
                mask = root / f"g{group}_v{view}.pgm"
                image.write_bytes(b"P6\n1 1\n255\n\x00\x00\x00")
                mask.write_bytes(b"P5\n1 1\n255\n\x00")
                records.append(DatasetRecord(f"s{group}_{view}", "wheat", "v1", f"plant-{group}",
                                             "unassigned", image, mask, "public"))
        return records

    def test_manifest_round_trip_and_group_split_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = self._records(root)
            source = root / "source.csv"
            write_manifest(records, source)
            loaded = read_manifest(source, require_split=False)
            first = split_by_group(loaded, seed=15)
            second = split_by_group(loaded, seed=15)
            self.assertEqual([row.split for row in first], [row.split for row in second])
            groups: dict[str, set[str]] = {}
            for row in first:
                groups.setdefault(row.group_id, set()).add(row.split)
            self.assertTrue(all(len(splits) == 1 for splits in groups.values()))
            self.assertEqual(sum(split_counts(first).values()), len(records))
            out = root / "split.csv"
            write_manifest(first, out, relative_to=root)
            reread = read_manifest(out)
            self.assertEqual(len(reread), len(records))

    def test_rejects_leaking_groups_and_invalid_source(self):
        with tempfile.TemporaryDirectory() as directory:
            records = self._records(Path(directory), groups=3)
            records[0] = DatasetRecord(records[0].sample_id, "wheat", "v1", records[0].group_id,
                                       "train", records[0].image_path, records[0].reference_mask_path, "public")
            records[1] = DatasetRecord(records[1].sample_id, "wheat", "v1", records[1].group_id,
                                       "test", records[1].image_path, records[1].reference_mask_path, "public")
            records[2] = DatasetRecord(records[2].sample_id, "wheat", "v1", records[2].group_id,
                                       "validation", records[2].image_path, records[2].reference_mask_path, "public")
            for index in range(3, len(records)):
                row = records[index]
                records[index] = DatasetRecord(row.sample_id, row.dataset_name, row.dataset_version,
                                               row.group_id, "validation", row.image_path,
                                               row.reference_mask_path, row.data_source)
            with self.assertRaisesRegex(ValueError, "跨数据划分"):
                validate_records(records)
            invalid = DatasetRecord("x", "wheat", "v1", "g", "train", records[2].image_path,
                                    records[2].reference_mask_path, "unknown")
            with self.assertRaisesRegex(ValueError, "来源无效"):
                validate_records([invalid])

    def test_split_requires_three_groups_and_valid_ratios(self):
        with tempfile.TemporaryDirectory() as directory:
            records = self._records(Path(directory), groups=2)
            with self.assertRaises(ValueError):
                split_by_group(records)
            with self.assertRaises(ValueError):
                split_by_group(records, train_ratio=.8, validation_ratio=.2, test_ratio=.2)


if __name__ == "__main__":
    unittest.main()
