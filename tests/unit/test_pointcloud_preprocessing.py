"""三维点云预处理模块的独立测试程序。"""

import tempfile
import unittest
from pathlib import Path

from wheat_phenotyping.pointcloud_preprocessing import (
    PointCloud,
    read_point_cloud_csv,
    voxel_downsample,
    write_point_cloud_csv,
)


class PointCloudPreprocessingTest(unittest.TestCase):
    """检查点云 CSV 读写、体素质心和标签多数票。"""

    def test_csv_round_trip_and_voxel_labels(self):
        cloud = PointCloud(((0.01, 0.01, 0.01), (0.02, 0.02, 0.02), (0.20, 0.20, 0.20)), (1, 1, 2))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cloud.csv"
            write_point_cloud_csv(cloud, path)
            loaded = read_point_cloud_csv(path)
            self.assertEqual(loaded.points, cloud.points)
            reduced = voxel_downsample(loaded, 0.1)
        self.assertEqual(len(reduced), 2)
        self.assertEqual(reduced.labels, (1, 2))
        self.assertAlmostEqual(reduced.points[0][0], 0.015)

    def test_rejects_nonpositive_voxel_size(self):
        with self.assertRaises(ValueError):
            voxel_downsample(PointCloud(((0.0, 0.0, 0.0),)), 0)


if __name__ == "__main__":
    unittest.main()
