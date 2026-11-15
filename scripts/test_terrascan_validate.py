import tempfile, unittest
from pathlib import Path
from scripts.terrascan_validate import validate

class ValidationTests(unittest.TestCase):
    def base(self, body='Mars', crs='EPSG:4326'):
        return {'body':body,'sha256':'a'*64,'rasterMetadata':{'available':True,'width':100,'height':50,'bandCount':1,'resolution':[0.01,-0.01],'bounds':[0,0,1,1],'crs':crs,'units':['m'],'nodataValues':[-9999]}}
    def test_earth_crs_rejected_for_mars(self):
        r=validate(self.base(), 'Mars')
        self.assertEqual(next(x for x in r['checks'] if x['rule']=='PLANETARY_CRS_GUARD')['status'],'fail')
        self.assertEqual(r['scientificDisposition'],'not-approved')
    def test_moon_with_unknown_crs_is_review_required(self):
        d=self.base('Moon', None)
        r=validate(d,'Moon')
        self.assertEqual(next(x for x in r['checks'] if x['rule']=='CRS_DECLARED')['status'],'unknown')
        self.assertEqual(r['summary']['overall'],'review-required')
    def test_body_mismatch_fails(self):
        r=validate(self.base('Earth', 'LOCAL_CS["Mars"]'),'Mars')
        self.assertEqual(next(x for x in r['checks'] if x['rule']=='BODY_EXPECTED')['status'],'fail')
    def test_invalid_resolution_fails(self):
        d=self.base(); d['rasterMetadata']['resolution']=[0,0]
        r=validate(d,'Mars')
        self.assertEqual(next(x for x in r['checks'] if x['rule']=='RASTER_RESOLUTION')['status'],'fail')
    def test_label_target_and_frame_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'label.xml'
            p.write_text('<Product><Target_Identification><name>Mars</name></Target_Identification><Coordinate_System_Identification><name>Mars 2000</name></Coordinate_System_Identification><unit>m</unit></Product>')
            r=validate(self.base('Mars','LOCAL_CS["Mars 2000"]'),'Mars',p)
            self.assertEqual(next(x for x in r['checks'] if x['rule']=='PDS_LABEL_PARSE')['status'],'pass')
            self.assertEqual(next(x for x in r['checks'] if x['rule']=='LABEL_TARGET_BODY')['status'],'pass')
            self.assertEqual(next(x for x in r['checks'] if x['rule']=='LABEL_REFERENCE_FRAME')['status'],'pass')
    def test_label_parse_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.xml'; p.write_text('<bad>')
            r=validate(self.base(),'Mars',p)
            self.assertEqual(next(x for x in r['checks'] if x['rule']=='PDS_LABEL_PARSE')['status'],'fail')
    def test_no_units_are_not_inferred(self):
        d=self.base(); d['rasterMetadata']['units']=None
        r=validate(d,'Mars')
        self.assertEqual(next(x for x in r['checks'] if x['rule']=='UNITS_DECLARED')['status'],'unknown')

if __name__=='__main__': unittest.main()
