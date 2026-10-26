import tempfile
import unittest
from pathlib import Path
from choreography.engine import smooth_segment
from flight_tracking import FlightTracker

class TrackingTests(unittest.TestCase):
    def test_expected_and_summary(self):
        segs = [smooth_segment([0,0,0,0],[0,0,1,0],4),
                smooth_segment([0,0,1,0],[1,0,1,0],5),
                smooth_segment([1,0,1,0],[1,0,0,0],4)]
        with tempfile.TemporaryDirectory() as d:
            tracker = FlightTracker({'CF01': segs}, Path(d)/'track.csv')
            self.assertAlmostEqual(tracker._expected('CF01','trajectory',5)[0],1)
            self.assertAlmostEqual(tracker._expected('CF01','hover',2)[2],1)
            tracker.set_phase('trajectory', start=100)
            tracker.record_command_start('CF01', instant=100)
            tracker._position('CF01',1000,{'stateEstimate.x':0.,'stateEstimate.y':0.,'stateEstimate.z':1.})
            self.assertEqual(tracker.summary()['CF01']['trajectory_samples'],1)
            tracker.close()
            self.assertTrue((Path(d)/'track.csv').exists())
