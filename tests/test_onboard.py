import unittest
import numpy as np
from choreography.engine import Segment
from onboard_execution import transform_paths, prepare

class OnboardTests(unittest.TestCase):
    def test_rigid_transform_coefficients(self):
        seg = Segment(2, [[1, 2, 0, 0, 0, 0, 0, 0],
                          [3, 0, 0, 0, 0, 0, 0, 0],
                          [1, 0, 0, 0, 0, 0, 0, 0],
                          [0, 0, 0, 0, 0, 0, 0, 0]])
        converted = transform_paths({'CF01':[seg]}, [10,20,2], 90)['CF01'][0]
        np.testing.assert_allclose(converted.evaluate(0)[:3], [7,21,3], atol=1e-8)
        np.testing.assert_allclose(converted.evaluate(1)[:3], [7,23,3], atol=1e-8)

    def test_demo_airborne_extraction(self):
        _, _, _, middle, duration, _ = prepare('shows/two_drone_demo.json', ['CF01'])
        self.assertEqual(len(middle['CF01']), 3)
        self.assertAlmostEqual(duration, 11.0)

if __name__ == '__main__':
    unittest.main()
