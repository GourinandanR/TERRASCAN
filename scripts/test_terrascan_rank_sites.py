import json,tempfile,unittest,hashlib
from pathlib import Path
from scripts.terrascan_rank_sites import run
def put(p,obj):
    p.write_text(json.dumps(obj)); return str(p)
def setup_case(td, eligible=True, approved=True):
    d=Path(td); sid="site-01"
    analog={"scientificDisposition":"exploratory-ranking-pending-human-review","evidenceApproval":"unchanged",
      "results":[{"id":sid,"status":"ranked","similarityScore":82.5}]}
    suitability={"id":"assessment-1","site_id":sid,"target_body":"Moon","status":"eligible" if eligible else "indeterminate",
      "input_snapshot":{"site_id":sid,"approved_evidence":[{"manifest_id":"m1","status":"approved"}] if approved else []}}
    ap=put(d/"analog.json",analog); sp=put(d/"suitability.json",suitability)
    payload={"schemaVersion":"terrascan.site-ranking-input.v1","targetBody":"Moon",
      "policy":{"analogWeight":0.8,"uncertaintyPenaltyWeight":0.2},
      "sites":[{"siteId":sid,"siteName":"Test Site","analogReport":ap,"suitabilitySnapshot":sp,"uncertaintyFraction":0.1}]}
    pp=put(d/"input.json",payload)
    return payload,Path(pp)
class TestSiteRanking(unittest.TestCase):
    def test_eligible_site_ranked_with_explanation_and_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            p,path=setup_case(td); r=run(p,path)
            self.assertEqual(r["rankedCount"],1)
            x=r["rankedSites"][0]
            self.assertEqual(x["rank"],1); self.assertIn("formula",x["explanation"])
            self.assertEqual(len(x["analogReportSha256"]),64)
    def test_ineligible_or_unknown_suitability_withheld(self):
        with tempfile.TemporaryDirectory() as td:
            p,path=setup_case(td,eligible=False); r=run(p,path)
            self.assertEqual(r["rankedCount"],0)
            self.assertIn("mission-constraints-not-eligible",r["withheldSites"][0]["reasons"])
    def test_missing_approved_evidence_withheld(self):
        with tempfile.TemporaryDirectory() as td:
            p,path=setup_case(td,approved=False); r=run(p,path)
            self.assertEqual(r["rankedCount"],0)
            self.assertIn("no-approved-evidence-recorded-in-suitability-snapshot",r["withheldSites"][0]["reasons"])
    def test_site_id_mismatch_withheld(self):
        with tempfile.TemporaryDirectory() as td:
            p,path=setup_case(td); p["sites"][0]["siteId"]="other"; r=run(p,path)
            self.assertEqual(r["rankedCount"],0)
    def test_uncertainty_must_be_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            p,path=setup_case(td); del p["sites"][0]["uncertaintyFraction"]; r=run(p,path)
            self.assertEqual(r["rankedCount"],0)
            self.assertIn("uncertaintyFraction-must-be-explicit-between-0-and-1",r["withheldSites"][0]["reasons"])
    def test_invalid_policy_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p,path=setup_case(td); p["policy"]["analogWeight"]=-1
            with self.assertRaisesRegex(ValueError,"finite non-negative"): run(p,path)
    def test_tie_break_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            p,path=setup_case(td)
            p["sites"].append(dict(p["sites"][0],siteId="site-00",siteName="Another Site"))
            # Duplicate suitability and analog results for the second ID.
            ap=Path(p["sites"][0]["analogReport"]); a=json.loads(ap.read_text()); a["results"].append({"id":"site-00","status":"ranked","similarityScore":82.5}); ap.write_text(json.dumps(a))
            sp=Path(p["sites"][0]["suitabilitySnapshot"]); s=json.loads(sp.read_text()); s["site_id"]="site-00"; s["input_snapshot"]["site_id"]="site-00"
            sp0=Path(td)/"suitability-00.json"; sp0.write_text(json.dumps(s)); p["sites"][1]["suitabilitySnapshot"]=str(sp0)
            r=run(p,path); self.assertEqual([x["siteId"] for x in r["rankedSites"]],["site-00","site-01"])
if __name__=="__main__": unittest.main()
