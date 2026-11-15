import importlib.util, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).with_name("terrascan_ingest.py")
spec=importlib.util.spec_from_file_location("ingest",SCRIPT)
ingest=importlib.util.module_from_spec(spec); spec.loader.exec_module(ingest)
class LabelInspectionTests(unittest.TestCase):
 def test_extracts_pds4_like_values_as_unvalidated_hints(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"label.xml"
   f.write_text('<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1"><Identification_Area><logical_identifier>urn:nasa:pds:test</logical_identifier><version_id>1.0</version_id><title>Fixture</title></Identification_Area></Product_Observational>')
   result=ingest.pds4_label_info(f); self.assertTrue(result["available"])
   self.assertEqual(result["extracted_values"]["logical_identifier"],["urn:nasa:pds:test"])
   self.assertIn("validate product class",result["warning"])
 def test_non_xml_file_is_not_parsed(self):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/"image.tif"; f.write_bytes(b"fixture")
   self.assertFalse(ingest.pds4_label_info(f)["available"])
if __name__=="__main__": unittest.main()
