import importlib.util, tempfile, unittest
from pathlib import Path

SCRIPT=Path(__file__).with_name('terrascan_pipeline.py')
spec=importlib.util.spec_from_file_location('pipeline',SCRIPT)
pipeline=importlib.util.module_from_spec(spec); spec.loader.exec_module(pipeline)

class PipelineSafetyTests(unittest.TestCase):
    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError): pipeline.safe_project_file('../../etc/passwd')
    def test_rejects_unknown_dataset(self):
        with tempfile.TemporaryDirectory(dir=pipeline.ROOT) as td:
            f=Path(td)/'x.bin'; f.write_bytes(b'x')
            with self.assertRaises(ValueError): pipeline.process_job({'dataset_id':'unknown','file':str(f.relative_to(pipeline.ROOT)),'source_url':'https://example.org/x','provider':'x'})
    def test_rejects_missing_input(self):
        with self.assertRaises(FileNotFoundError): pipeline.safe_project_file('this-file-does-not-exist.bin')
    def test_hash_is_stable(self):
        with tempfile.TemporaryDirectory(dir=pipeline.ROOT) as td:
            f=Path(td)/'sample'; f.write_bytes(b'terrascan')
            self.assertEqual(pipeline.sha256(f),pipeline.sha256(f))
    def test_config_template_has_empty_jobs(self):
        import json
        cfg=json.loads((pipeline.ROOT/'data/pipeline/jobs.example.json').read_text())
        self.assertEqual(cfg,{'jobs':[]})

if __name__=='__main__': unittest.main()
