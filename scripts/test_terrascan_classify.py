import json, tempfile, unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scripts.terrascan_classify import classify

class Args: pass

class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name)
        self.raster=self.base/"surface.tif"
        y,x=np.mgrid[0:30,0:30]
        z=(x*2+y).astype("float32")
        with rasterio.open(self.raster,"w",driver="GTiff",width=30,height=30,count=1,
                           dtype="float32",crs="EPSG:32643",
                           transform=from_origin(500000,1200000,30,30),nodata=-9999) as ds:
            ds.write(z,1); ds.set_band_unit(1,"m")
        self.validation=self.base/"validation.json"
        self.validation.write_text(json.dumps({"expectedBody":"Mars","summary":{"overall":"review-required","fail":0,"unknown":1}}))
        self.config=self.base/"classes.json"
        self.config.write_text(json.dumps({"schemaVersion":"1.0","name":"test rules","classes":[
            {"name":"gentle-low-relief","slopeDegrees":[0,89],"tpi":[-100,100],"localStdDev":[0,1000]}
        ]}))
        self.raster_out=self.base/"classified.tif"; self.report_out=self.base/"report.json"

    def tearDown(self): self.tmp.cleanup()

    def args(self):
        a=Args(); a.input=str(self.raster); a.validation_report=str(self.validation)
        a.config=str(self.config); a.body="Mars"; a.band=1; a.window=3
        a.pixel_size_units="m"; a.vertical_units="m"
        a.output_raster=str(self.raster_out); a.output_report=str(self.report_out)
        return a

    def test_classification_outputs_and_hashes(self):
        result=classify(self.args())
        payload=json.loads(self.report_out.read_text())
        self.assertEqual(result["counts"]["classifiedPixels"],28*28)
        self.assertEqual(payload["evidenceApproval"],"unchanged")
        self.assertEqual(payload["similarityScores"],"not-computed")
        with rasterio.open(self.raster_out) as ds:
            self.assertEqual(ds.dtypes[0],"uint16")
            self.assertEqual(int(ds.read(1).max()),1)

    def test_body_mismatch_blocked(self):
        a=self.args(); a.body="Moon"
        with self.assertRaisesRegex(ValueError,"body mismatch"): classify(a)

    def test_invalid_rule_ranges_rejected(self):
        self.config.write_text(json.dumps({"schemaVersion":"1.0","classes":[
            {"name":"bad","slopeDegrees":[5,1],"tpi":[0,1],"localStdDev":[0,1]}]}))
        with self.assertRaisesRegex(ValueError,"Reversed range"): classify(self.args())

    def test_output_overwrite_blocked(self):
        classify(self.args())
        with self.assertRaisesRegex(FileExistsError,"refusing to overwrite"): classify(self.args())

    def test_failed_validation_blocks(self):
        self.validation.write_text(json.dumps({"expectedBody":"Mars","summary":{"fail":1}}))
        with self.assertRaisesRegex(ValueError,"failed checks"): classify(self.args())

if __name__=="__main__": unittest.main()
