import json, tempfile, unittest
from pathlib import Path
from scripts.terrascan_ml import SCHEMA, load_dataset, train, predict

HASH="a"*64
def dataset():
    samples=[]
    for cls,base in (("smooth",0.0),("rough",10.0)):
        for i in range(8):
            samples.append({"sample_id":f"{cls}-{i}","label":cls,
                "features":{"slope_mean":base+i*.01,"roughness":base+i*.02},
                "source":{"source_id":"synthetic-test-fixture","sha256":HASH},
                "label_basis":"Synthetic software-test fixture only"})
    return {"schema_version":SCHEMA,"feature_names":["slope_mean","roughness"],"samples":samples}

class TestTerrascanML(unittest.TestCase):
    def test_empty_samples_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"empty.json"; p.write_text(json.dumps({"schema_version":SCHEMA,"feature_names":["x"],"samples":[]}))
            with self.assertRaisesRegex(ValueError,"No labelled samples"):
                load_dataset(p)

    def test_feature_schema_mismatch_rejected(self):
        d=dataset(); d["samples"][0]["features"]={"slope_mean":1}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"; p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,"exactly match"):
                load_dataset(p)

    def test_invalid_provenance_rejected(self):
        d=dataset(); d["samples"][0]["source"]["sha256"]="not-a-hash"
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"; p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                load_dataset(p)

    def test_each_class_needs_two_samples(self):
        d=dataset(); d["samples"]=[s for s in d["samples"] if s["label"]=="smooth"]+[d["samples"][-1]]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"; p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,"two samples"):
                load_dataset(p)

    def test_train_and_predict_are_review_gated(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); src=base/"training.json"; src.write_text(json.dumps(dataset()))
            out=base/"trained"
            metrics=train(src,out,seed=7,trees=30)
            self.assertEqual(metrics["status"],"trained-evaluated")
            self.assertEqual(metrics["review_status"],"pending-human-review")
            self.assertTrue((out/"model.joblib").exists())
            inference={"feature_names":["slope_mean","roughness"],"samples":[
                {"sample_id":"unseen-1","features":{"slope_mean":0.02,"roughness":0.03}}]}
            inp=base/"inference.json"; inp.write_text(json.dumps(inference))
            result=predict(out/"model.joblib",inp,base/"predictions.json")
            self.assertEqual(result["status"],"exploratory-pending-human-review")
            self.assertEqual(result["results"][0]["review_status"],"pending-human-review")
            self.assertIn("different planetary body",result["limitations"][1])

    def test_inference_feature_order_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); src=base/"training.json"; src.write_text(json.dumps(dataset()))
            out=base/"trained"; train(src,out,trees=20)
            inp=base/"inference.json"; inp.write_text(json.dumps({"feature_names":["roughness","slope_mean"],"samples":[{"features":{"slope_mean":1,"roughness":2}}]}))
            with self.assertRaisesRegex(ValueError,"exactly match"):
                predict(out/"model.joblib",inp,base/"pred.json")

if __name__=="__main__": unittest.main()
