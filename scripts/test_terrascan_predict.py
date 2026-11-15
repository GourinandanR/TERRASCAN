import json, tempfile, unittest
from pathlib import Path
from scripts.terrascan_predict import SCHEMA, load_data, fit, predict
H="b"*64
def fixture():
    samples=[]
    for g in range(12):
        for j in range(3):
            x=float(g*2+j*.1)
            samples.append({"sample_id":f"g{g}-s{j}","spatial_group_id":f"tile-{g}",
              "features":{"slope":x,"roughness":x*.5+1},"target_value":x*1.8+3,
              "target_basis":"Synthetic test-only target formula",
              "source":{"source_id":"synthetic-unit-test-only","sha256":H}})
    return {"schema_version":SCHEMA,"feature_names":["slope","roughness"],
      "target":{"name":"test_target","unit":"arbitrary_test_units"},"samples":samples}
class TestPredictiveTerrain(unittest.TestCase):
    def write(self,td,d):
        p=Path(td)/"training.json"; p.write_text(json.dumps(d)); return p
    def test_missing_group_id_rejected(self):
        d=fixture(); del d["samples"][0]["spatial_group_id"]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"spatial_group_id"): load_data(self.write(td,d))
    def test_insufficient_groups_rejected(self):
        d=fixture()
        for s in d["samples"]: s["spatial_group_id"]="one-group"
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"six distinct"): load_data(self.write(td,d))
    def test_feature_schema_mismatch_rejected(self):
        d=fixture(); d["samples"][0]["features"]={"slope":2}
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"exactly match"): load_data(self.write(td,d))
    def test_nonfinite_target_rejected(self):
        d=fixture(); d["samples"][0]["target_value"]=float("nan")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"finite numeric"): load_data(self.write(td,d))
    def test_train_report_has_separate_group_splits_and_uncertainty(self):
        with tempfile.TemporaryDirectory() as td:
            src=self.write(td,fixture()); out=Path(td)/"model"
            r=fit(src,out,seed=13,trees=30)
            self.assertEqual(r["status"],"trained-evaluated")
            self.assertFalse(r["split"]["group_overlap"])
            self.assertGreater(r["interval"]["absolute_residual_radius"],0)
            self.assertIn("mae",r["metrics"]); self.assertIn("rmse",r["metrics"])
            self.assertEqual(r["review_status"],"pending-human-review")
    def test_predict_outputs_bounds_and_review_gate(self):
        with tempfile.TemporaryDirectory() as td:
            src=self.write(td,fixture()); out=Path(td)/"model"; fit(src,out,trees=30)
            inp=Path(td)/"input.json"
            inp.write_text(json.dumps({"feature_names":["slope","roughness"],"samples":[{"sample_id":"new","features":{"slope":2.0,"roughness":2.0}}]}))
            r=predict(out/"regressor.joblib",inp,Path(td)/"predictions.json")
            item=r["results"][0]
            self.assertLessEqual(item["lower_bound"],item["predicted_value"])
            self.assertGreaterEqual(item["upper_bound"],item["predicted_value"])
            self.assertEqual(item["review_status"],"pending-human-review")
    def test_inference_schema_order_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src=self.write(td,fixture()); out=Path(td)/"model"; fit(src,out,trees=20)
            inp=Path(td)/"input.json"; inp.write_text(json.dumps({"feature_names":["roughness","slope"],"samples":[]}))
            with self.assertRaisesRegex(ValueError,"exactly match"): predict(out/"regressor.joblib",inp,Path(td)/"o.json")
if __name__=="__main__": unittest.main()
