import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import rasterio
from rasterio.transform import from_origin
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import terrascan_features

class FeatureExtractionTests(unittest.TestCase):
    def test_extracts_provenanced_pending_features(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td); transform = from_origin(500000, 1000, 10, 10)
            crs = "EPSG:32619"
            def raster(name, arr, unit=None):
                path = d/name
                with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                                   count=1, dtype=arr.dtype, crs=crs, transform=transform, nodata=-9999) as ds:
                    ds.write(arr, 1)
                    if unit: ds.set_band_unit(1, unit)
                return path
            dem = raster("dem.tif", np.array([[100,101,102,103],[100,102,104,106],[99,101,103,105],[98,100,102,104]], dtype="float32"), "m")
            slope = raster("slope.tif", np.full((4,4), 10, dtype="float32"), "degree")
            thermal = raster("thermal.tif", np.full((4,4), 250, dtype="float32"), "K")
            geology = raster("geology.tif", np.ones((4,4), dtype="int16"))
            zones = d/"zones.geojson"
            zones.write_text(json.dumps({"type":"FeatureCollection","features":[
                {"type":"Feature","properties":{"site":"candidate-a"},"geometry":{"type":"Polygon","coordinates":[[[500000,1000],[500040,1000],[500040,960],[500000,960],[500000,1000]]]}}
            ]}))
            classes = d/"classes.json"; classes.write_text(json.dumps({"1":"basalt"}))
            outdir = terrascan_features.OUT
            original = terrascan_features.OUT
            terrascan_features.OUT = d/"out"
            try:
                args = SimpleNamespace(geojson=str(zones), zone_crs=crs, dem=str(dem), slope=str(slope),
                    thermal=str(thermal), geology=str(geology), dem_band=1, slope_band=1, thermal_band=1,
                    geology_band=1, site_id_field="site", geology_classes=str(classes), roughness_radius=1,
                    all_touched=False, output_name="test", overwrite=False)
                terrascan_features.extract(args)
                result = json.loads((d/"out"/"test.features.json").read_text())
                self.assertEqual(result["status"], "pending-human-review")
                self.assertEqual(len(result["sites"]), 1)
                feats = result["sites"][0]["features"]
                self.assertAlmostEqual(feats["slope"]["value"], 10.0, places=5)
                self.assertAlmostEqual(feats["thermal"]["value"], 250.0, places=5)
                self.assertEqual(feats["geology"]["value"], "basalt")
                self.assertIsNotNone(feats["elevationRange"]["value"])
                self.assertEqual(len(result["sources"]), 4)
            finally:
                terrascan_features.OUT = original

if __name__ == "__main__": unittest.main()
