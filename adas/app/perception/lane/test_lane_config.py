import unittest

import lane_config


class LaneConfigTests(unittest.TestCase):
    def test_warp_coordinates_are_inside_configured_image(self):
        max_x = lane_config.IMAGE_WIDTH - 1
        max_y = lane_config.IMAGE_HEIGHT - 1

        for label, points in (("WARP_SRC", lane_config.WARP_SRC), ("WARP_DST", lane_config.WARP_DST)):
            for x, y in points:
                self.assertGreaterEqual(x, 0, label)
                self.assertLessEqual(x, max_x, label)
                self.assertGreaterEqual(y, 0, label)
                self.assertLessEqual(y, max_y, label)


if __name__ == "__main__":
    unittest.main()
