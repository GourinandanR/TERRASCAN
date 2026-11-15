import hashlib,json,tempfile,unittest
from pathlib import Path
from scripts.terrascan_qa import check_project,verify_artifact_manifest
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
class TestIntegratedQA(unittest.TestCase):
 def test_current_project_structure_passes(self):
  r=check_project(ROOT); self.assertEqual(r["status"],"pass",r["checks"])
 def test_manifest_verifies_file_hash(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td); f=d/"evidence.bin"; f.write_bytes(b"verified")
   m=d/"manifest.json"; m.write_text(json.dumps({"artifacts":[{"path":"evidence.bin","sha256":sha(f)}]}))
   r=verify_artifact_manifest(m); self.assertEqual(r["status"],"pass")
 def test_manifest_detects_tampering(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td); f=d/"evidence.bin"; f.write_bytes(b"original")
   m=d/"manifest.json"; m.write_text(json.dumps({"artifacts":[{"path":"evidence.bin","sha256":sha(f)}]}))
   f.write_bytes(b"tampered")
   r=verify_artifact_manifest(m); self.assertEqual(r["status"],"fail"); self.assertEqual(r["failed"],1)
 def test_missing_manifest_artifact_fails(self):
  with tempfile.TemporaryDirectory() as td:
   m=Path(td)/"manifest.json"; m.write_text(json.dumps({"artifacts":[{"path":"missing","sha256":"0"*64}]}))
   self.assertEqual(verify_artifact_manifest(m)["status"],"fail")
 def test_empty_manifest_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   m=Path(td)/"manifest.json"; m.write_text(json.dumps({"artifacts":[]}))
   with self.assertRaisesRegex(ValueError,"non-empty"): verify_artifact_manifest(m)
if __name__=="__main__": unittest.main()
