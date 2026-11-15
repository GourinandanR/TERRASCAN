import importlib.util, tempfile, unittest, json, hashlib, contextlib, io
from pathlib import Path
SCRIPT=Path(__file__).with_name("terrascan_pds.py")
spec=importlib.util.spec_from_file_location("terrascan_pds",SCRIPT)
pds=importlib.util.module_from_spec(spec); spec.loader.exec_module(pds)
class PdsDiscoveryTests(unittest.TestCase):
 def test_normalizes_common_fields_without_dropping_raw_record(self):
  raw={"lid":"urn:nasa:pds:test","title":"Example product","product_class":"Product_Observational"}
  out=pds.normalize_product(raw)
  self.assertEqual(out["lid"],raw["lid"]); self.assertEqual(out["title"],raw["title"])
  self.assertEqual(out["raw_record"],raw)
 def test_snapshot_hash_and_discovery_only_warning(self):
  with tempfile.TemporaryDirectory() as td:
   old=pds.OUT; old_root=pds.ROOT; pds.OUT=Path(td); pds.ROOT=Path(td)
   try:
    payload={"data":[{"lid":"urn:nasa:pds:test","title":"Test"}]}; raw=json.dumps(payload).encode()
    with contextlib.redirect_stdout(io.StringIO()): pds.save_snapshot("search","https://pds.nasa.gov/api/search/1/products",payload,raw)
    files=list(Path(td).glob("*.json")); self.assertEqual(len(files),1)
    doc=json.loads(files[0].read_text()); self.assertEqual(doc["response_sha256"],hashlib.sha256(raw).hexdigest())
    self.assertEqual(doc["record_count"],1); self.assertIn("not downloaded science data",doc["limitations"][1])
   finally: pds.OUT=old; pds.ROOT=old_root
 def test_identifier_requires_pds_lid(self):
  class Args: identifier="not-a-lid"
  with self.assertRaises(ValueError): pds.resolve(Args())
if __name__=="__main__": unittest.main()
