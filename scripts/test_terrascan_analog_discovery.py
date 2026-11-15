import hashlib, json, tempfile, unittest
from pathlib import Path
from scripts.terrascan_analog_discovery import run

class AnalogDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name)
        self.input=self.base/"input.json"
        h="a"*64
        feature=lambda value: {"value":value,"unit":"m","status":"approved","manifestStatus":"approved","sourceSha256":h}
        self.payload={"target":{"id":"mars-target-01","body":"Mars","features":{"elevation":feature(1000),"roughness":feature(5)}},
            "featureDefinitions":[{"name":"elevation","unit":"m","weight":2,"tolerance":100},
                                  {"name":"roughness","unit":"m","weight":1,"tolerance":10}],
            "candidates":[
                {"id":"earth-a","name":"Candidate A","body":"Earth","features":{"elevation":feature(1050),"roughness":feature(5)}},
                {"id":"earth-b","name":"Candidate B","body":"Earth","features":{"elevation":feature(1100),"roughness":feature(15)}},
                {"id":"earth-c","name":"Candidate C","body":"Earth","features":{"elevation":feature(900)}}]}
        self.input.write_text(json.dumps(self.payload))

    def tearDown(self): self.tmp.cleanup()

    def test_deterministic_rank_and_weighted_score(self):
        r=run(self.payload,self.input)
        self.assertEqual(r["rankedCount"],2)
        self.assertEqual(r["results"][0]["id"],"earth-a")
        self.assertEqual(r["results"][0]["similarityScore"],66.6667)
        self.assertEqual(r["results"][1]["similarityScore"],0.0)
        self.assertEqual(r["results"][-1]["status"],"unranked-incomplete")

    def test_unapproved_feature_withholds_ranking(self):
        p=json.loads(json.dumps(self.payload))
        p["candidates"][0]["features"]["elevation"]["status"]="pending-human-review"
        r=run(p,self.input)
        self.assertEqual(next(x for x in r["results"] if x["id"]=="earth-a")["status"],"unranked-incomplete")

    def test_unit_mismatch_withholds_ranking(self):
        p=json.loads(json.dumps(self.payload))
        p["candidates"][0]["features"]["roughness"]["unit"]="km"
        r=run(p,self.input)
        self.assertEqual(r["results"][0]["status"],"ranked")
        self.assertEqual(r["results"][-1]["status"],"unranked-incomplete")

    def test_non_earth_candidate_excluded(self):
        p=json.loads(json.dumps(self.payload)); p["candidates"][0]["body"]="Moon"
        r=run(p,self.input)
        self.assertEqual(r["results"][0]["status"],"ranked")
        self.assertTrue(any(x.get("id")=="earth-a" and x["status"]=="excluded" for x in r["results"]))

    def test_invalid_target_body_rejected(self):
        p=json.loads(json.dumps(self.payload)); p["target"]["body"]="Earth"
        with self.assertRaisesRegex(ValueError,"Moon or Mars"): run(p,self.input)

    def test_bad_hash_rejected_for_feature(self):
        p=json.loads(json.dumps(self.payload)); p["target"]["features"]["elevation"]["sourceSha256"]="bad"
        r=run(p,self.input)
        self.assertFalse(r["targetReady"])

if __name__=="__main__": unittest.main()
