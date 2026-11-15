import json, tempfile, unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts.terrascan_spatial import run

class Args: pass

class SpatialAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.raster = self.base / "synthetic.tif"
        data = np.arange(400, dtype="float32").reshape(20, 20)
        with rasterio.open(self.raster, "w", driver="GTiff", width=20, height=20,
                           count=1, dtype="float32", crs="EPSG:32643",
                           transform=from_origin(500000, 1200000, 30, 30), nodata=-9999) as ds:
            ds.write(data, 1)
            ds.set_band_unit(1, "m")
        self.validation = self.base / "validation.json"
        self.validation.write_text(json.dumps({"expectedBody":"Mars","summary":{"overall":"review-required","fail":0,"unknown":2}}))
        self.output = self.base / "result.json"

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, report=None, body="Mars"):
        a=Args(); a.input=str(self.raster); a.validation_report=str(report or self.validation)
        a.body=body; a.band=1; a.windows=[3,7]; a.pixel_size_units="m"; a.output=str(self.output)
        return a

    def test_multiscale_report_created_and_hash_bound(self):
        result=run(self.args())
        payload=json.loads(self.output.read_text())
        self.assertEqual(result["scales"],2)
        self.assertEqual(payload["scientificDisposition"],"descriptive-only-pending-human-review")
        self.assertEqual(payload["evidenceApproval"],"unchanged")
        self.assertEqual(payload["scales"][0]["topographicPositionIndex"]["count"],324)

    def test_body_mismatch_blocked(self):
        with self.assertRaisesRegex(ValueError,"body does not match"):
            run(self.args(body="Moon"))

    def test_failed_stage22_validation_blocks(self):
        bad=self.base/"bad.json"
        bad.write_text(json.dumps({"expectedBody":"Mars","summary":{"fail":1}}))
        with self.assertRaisesRegex(ValueError,"failed checks"):
            run(self.args(report=bad))

    def test_report_not_overwritten(self):
        run(self.args())
        with self.assertRaises(FileExistsError):
            run(self.args())

    def test_units_must_be_explicit(self):
        a=self.args(); a.pixel_size_units=""
        with self.assertRaisesRegex(ValueError,"pixel-size-units"):
            run(a)

if __name__ == "__main__":
    unittest.main()
