import unittest
from pathlib import Path
import numpy as np
from choreography.engine import load_show, generate, validate, smooth_segment

ROOT = Path(__file__).resolve().parents[1]

class EngineTests(unittest.TestCase):
    def test_endpoints_and_derivatives(self):
        s = smooth_segment([0,0,0,0], [1,2,3,0], 4)
        np.testing.assert_allclose(s.evaluate(0), [0,0,0,0])
        np.testing.assert_allclose(s.evaluate(4), [1,2,3,0], atol=1e-10)
        for axis in s.axes:
            self.assertAlmostEqual(axis[1], 0)
    def test_demos(self):
        for name in ('two_drone_demo.json', 'ten_drone_grid.json'):
            spec, names, pads = load_show(ROOT/'shows'/name)
            result = validate(generate(spec,names,pads),spec)
            self.assertTrue(result['ok'], result['issues'])
    def test_collision_detection(self):
        spec,names,pads = load_show(ROOT/'shows'/'two_drone_demo.json')
        spec['launch_positions_room_m']['CF02']=[-0.7,0,0]
        spec,names,pads = spec,names,np.array([spec['launch_positions_room_m'][n] for n in names])
        result = validate(generate(spec,names,pads),spec)
        self.assertFalse(result['ok'])

if __name__ == '__main__': unittest.main()
