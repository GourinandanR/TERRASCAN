"""API smoke tests; run from repository root with pytest installed."""
import os, tempfile
from fastapi.testclient import TestClient

fd, db_path = tempfile.mkstemp(suffix='.sqlite3')
os.close(fd)
os.environ['TERRASCAN_DB_PATH'] = db_path
from app.main import app

client_context = TestClient(app)
client = client_context

def setup_module():
    client_context.__enter__()

def teardown_module():
    client_context.__exit__(None, None, None)
    try: os.unlink(db_path)
    except OSError: pass

def test_health():
    assert client.get('/api/health').json()['status'] == 'ok'

def test_manifest_gate_and_observation():
    manifest = client.post('/api/manifests', json={
        'dataset_id':'fixture-dataset','version':'1','sha256':'a'*64,
        'source_uri':'https://example.org/product.tif'
    })
    assert manifest.status_code == 201, manifest.text
    m = manifest.json()
    blocked = client.post('/api/observations', json={
        'site_id':'fixture-site','target_body':'Earth','criterion':'slope',
        'value':12.5,'unit':'degree','manifest_id':m['id'],'quality':'reviewed'
    })
    assert blocked.status_code == 409

def test_manifest_approval_required_for_evidence():
    approved = client.post('/api/manifests', json={
        'dataset_id':'approved-dataset','version':'1','sha256':'b'*64,
        'source_uri':'https://example.org/approved.tif'
    })
    assert approved.status_code == 201
    m = approved.json()
    decision = client.post(f"/api/manifests/{m['id']}/review", json={'decision':'approved','reason':'Fixture source checked by reviewer.','reviewer':'test-suite'})
    assert decision.status_code == 200
    obs = client.post('/api/observations', json={
        'site_id':'site-a','target_body':'Earth','criterion':'slope','value':3.0,
        'unit':'degree','manifest_id':m['id'],'quality':'label-verified'
    })
    assert obs.status_code == 201, obs.text

def test_target_profile_and_comparison_snapshot():
    profile = client.post('/api/target-profiles', json={
        'target_body':'Mars','feature_key':'slope_distribution','value':8.0,'unit':'degree'
    })
    assert profile.status_code == 201, profile.text
    run = client.post('/api/comparison-runs', json={'target_body':'Mars'})
    assert run.status_code == 201, run.text
    payload = run.json()
    assert payload['status'] == 'queued'
    assert payload['input_snapshot']['scoring_status'] == 'not-computed-by-api'
    assert len(payload['input_snapshot']['target_profiles']) == 1

def test_manifest_checksum_validation():
    response = client.post('/api/manifests', json={
        'dataset_id':'bad-checksum','version':'1','sha256':'not-a-hash',
        'source_uri':'https://example.org/data'
    })
    assert response.status_code == 422


def test_manifest_and_observation_review_workflow():
    manifest = client.post('/api/manifests', json={
        'dataset_id':'review-dataset','version':'1','sha256':'c'*64,
        'source_uri':'https://example.org/review.tif'
    })
    assert manifest.status_code == 201
    mid = manifest.json()['id']
    obs_blocked = client.post('/api/observations', json={
        'site_id':'review-site','target_body':'Earth','criterion':'thermal','value':250,
        'unit':'K','manifest_id':mid,'quality':'unassessed'
    })
    assert obs_blocked.status_code == 409
    decision = client.post(f'/api/manifests/{mid}/review', json={
        'decision':'approved','reason':'Official label and provenance checked.',
        'reviewer':'reviewer-test'
    })
    assert decision.status_code == 200
    obs = client.post('/api/observations', json={
        'site_id':'review-site','target_body':'Earth','criterion':'thermal','value':250,
        'unit':'K','manifest_id':mid,'quality':'medium'
    })
    assert obs.status_code == 201
    oid = obs.json()['id']
    assert obs.json()['review_status'] == 'pending-human-review'
    rejected = client.post(f'/api/observations/{oid}/review', json={
        'decision':'rejected','reason':'Temporal coverage is not comparable.',
        'reviewer':'reviewer-test'
    })
    assert rejected.status_code == 200
    assert rejected.json()['review_status'] == 'rejected'
    repeated = client.post(f'/api/observations/{oid}/review', json={
        'decision':'approved','reason':'Try to change decision after review.',
        'reviewer':'reviewer-test'
    })
    assert repeated.status_code == 409

def test_review_queue_and_history():
    queue = client.get('/api/review-queue')
    assert queue.status_code == 200
    assert 'manifests' in queue.json() and 'observations' in queue.json()
    history = client.get('/api/review-history')
    assert history.status_code == 200
    assert len(history.json()['items']) >= 2

def test_comparison_snapshot_excludes_unreviewed_observations():
    run = client.post('/api/comparison-runs', json={'target_body':'Mars'})
    assert run.status_code == 201
    observations = run.json()['input_snapshot']['observations']
    assert all(item.get('review_status') == 'approved' for item in observations)


def test_approved_observation_enters_comparison_snapshot():
    manifest = client.post('/api/manifests', json={
        'dataset_id':'approved-observation-source','version':'1','sha256':'d'*64,
        'source_uri':'https://example.org/approved-observation.tif'
    })
    mid = manifest.json()['id']
    mr = client.post(f'/api/manifests/{mid}/review', json={
        'decision':'approved','reason':'Source metadata and provenance verified.',
        'reviewer':'reviewer-approved'
    })
    assert mr.status_code == 200
    obs = client.post('/api/observations', json={
        'site_id':'candidate-1','target_body':'Earth','criterion':'slope','value':4.2,
        'unit':'degree','manifest_id':mid,'quality':'high'
    })
    oid = obs.json()['id']
    approved = client.post(f'/api/observations/{oid}/review', json={
        'decision':'approved','reason':'Value, unit and extraction method checked.',
        'reviewer':'reviewer-approved'
    })
    assert approved.status_code == 200
    assert approved.json()['review_status'] == 'approved'
    run = client.post('/api/comparison-runs', json={'target_body':'Moon'})
    snapshot = run.json()['input_snapshot']['observations']
    assert any(item['id'] == oid for item in snapshot)


def test_scientific_report_summary_and_csv_export():
    summary = client.get('/api/reports/Mars/summary')
    assert summary.status_code == 200
    payload = summary.json()
    assert payload['target_body'] == 'Mars'
    assert payload['comparison_status'] == 'not-computed'
    assert 'observations' in payload and 'target_references' in payload
    csv_response = client.get('/api/reports/Mars/csv')
    assert csv_response.status_code == 200
    assert 'text/csv' in csv_response.headers['content-type']
    assert 'site_id,criterion' in csv_response.text
    assert 'not computed' not in csv_response.text.lower() or 'not-computed' not in csv_response.text.lower()

def test_scientific_report_pdf_export():
    response = client.get('/api/reports/Moon/pdf')
    assert response.status_code == 200, response.text[:500]
    assert response.headers['content-type'] == 'application/pdf'
    assert response.content.startswith(b'%PDF-')
    assert 'attachment;' in response.headers['content-disposition']


def _mission_profile(profile_id, criteria):
    return client.post('/api/mission-profiles', json={
        'id': profile_id, 'name': 'Test profile', 'target_body': 'Earth',
        'description': 'Test-only unvalidated limits', 'criteria': criteria
    })

def _approved_observation(site, criterion, value, unit, suffix):
    m = client.post('/api/manifests', json={
        'dataset_id': f'mission-{suffix}', 'version': '1', 'sha256': suffix[0]*64,
        'source_uri': f'https://example.org/{suffix}.tif'
    })
    assert m.status_code == 201, m.text
    decision = client.post(f"/api/manifests/{m.json()['id']}/review", json={'decision':'approved','reason':'Test fixture source reviewed.','reviewer':'test-suite'})
    assert decision.status_code == 200
    o = client.post('/api/observations', json={
        'site_id': site, 'target_body': 'Earth', 'criterion': criterion, 'value': value,
        'unit': unit, 'manifest_id': m.json()['id'], 'quality': 'test-fixture'
    })
    assert o.status_code == 201, o.text
    reviewed = client.post(f"/api/observations/{o.json()['id']}/review", json={
        'decision': 'approved', 'reason': 'Test fixture validated for API test.', 'reviewer': 'test-suite'
    })
    assert reviewed.status_code == 200
    return o.json()['id']

def test_suitability_missing_evidence_is_indeterminate_and_snapshot_immutable():
    p = _mission_profile('profile-missing', [{'key':'slope','unit':'deg','minimum':0,'maximum':10,'required':True}])
    assert p.status_code == 201, p.text
    run = client.post('/api/suitability-assessments', json={'profile_id':'profile-missing','profile_revision':1,'site_id':'empty-site'})
    assert run.status_code == 201, run.text
    payload = run.json()
    assert payload['status'] == 'indeterminate'
    assert payload['result']['constraints'][0]['status'] == 'unknown'
    saved = client.get(f"/api/suitability-assessments/{payload['id']}").json()
    assert saved['input_snapshot'] == payload['input_snapshot']

def test_suitability_inclusive_boundary_pass_and_failure_gate():
    _approved_observation('boundary-site','slope',10,'deg','d')
    p = _mission_profile('profile-boundary', [{'key':'slope','unit':'deg','minimum':0,'maximum':10,'required':True}])
    assert p.status_code == 201, p.text
    run = client.post('/api/suitability-assessments', json={'profile_id':'profile-boundary','profile_revision':1,'site_id':'boundary-site'})
    assert run.json()['status'] == 'eligible'
    _approved_observation('fail-site','slope',10.1,'deg','e')
    failed = client.post('/api/suitability-assessments', json={'profile_id':'profile-boundary','profile_revision':1,'site_id':'fail-site'})
    assert failed.json()['status'] == 'ineligible'
    assert failed.json()['result']['constraints'][0]['status'] == 'fail'

def test_suitability_unapproved_evidence_and_unit_mismatch_remain_unknown():
    m = client.post('/api/manifests', json={'dataset_id':'pending-mission','version':'1','sha256':'f'*64,'source_uri':'https://example.org/pending.tif'})
    assert m.status_code == 201
    o = client.post('/api/observations', json={'site_id':'unit-site','target_body':'Earth','criterion':'slope','value':4,'unit':'degree','manifest_id':m.json()['id'],'quality':'pending'})
    assert o.status_code == 409
    _approved_observation('unit-site','slope',4,'degree','a')
    p = _mission_profile('profile-unit', [{'key':'slope','unit':'deg','minimum':0,'maximum':10,'required':True}])
    assert p.status_code == 201
    run = client.post('/api/suitability-assessments', json={'profile_id':'profile-unit','profile_revision':1,'site_id':'unit-site'})
    assert run.json()['status'] == 'indeterminate'
    assert run.json()['result']['constraints'][0]['status'] == 'unknown'

def test_mission_profile_revisions_are_immutable_and_bad_bounds_rejected():
    criteria=[{'key':'roughness','unit':'m','minimum':0,'maximum':1,'required':True}]
    first=_mission_profile('profile-revision',criteria)
    second=_mission_profile('profile-revision',criteria)
    assert first.json()['revision']==1 and second.json()['revision']==2
    bad=client.post('/api/mission-profiles',json={'name':'bad','target_body':'Moon','criteria':[{'key':'x','unit':'m','minimum':5,'maximum':1}]})
    assert bad.status_code==422

def test_manifest_cannot_self_approve_on_creation():
    response = client.post('/api/manifests', json={
        'dataset_id':'self-approval-attempt','version':'1','sha256':'9'*64,
        'source_uri':'https://example.org/self-approval.tif','review_status':'approved'
    })
    assert response.status_code == 422


def test_mission_scenario_dependency_schedule_and_snapshot():
    response = client.post('/api/mission-scenarios', json={
        'name':'fixture-scenario','target_body':'Mars','site_id':'fixture-site',
        'activities':[
            {'id':'a','name':'Survey','duration_hours':4,'depends_on':[],'resources':{'power':3}},
            {'id':'b','name':'Deploy','duration_hours':2,'depends_on':['a'],'resources':{'power':5}},
            {'id':'c','name':'Parallel prep','duration_hours':3,'depends_on':[],'resources':{}}
        ], 'resource_limits':{'power':4}
    })
    assert response.status_code == 201, response.text
    data=response.json()
    assert data['result']['duration_hours'] == 6
    assert next(x for x in data['result']['schedule'] if x['activity_id']=='b')['start_hour'] == 4
    assert data['status'] == 'resource-constrained'
    saved=client.get('/api/mission-scenarios/'+data['id']).json()
    assert saved['input_snapshot'] == data['input_snapshot']
    assert saved['result'] == data['result']


def test_mission_scenario_rejects_cycles_and_unknown_dependencies():
    base={'name':'bad-scenario','target_body':'Moon','site_id':'s','resource_limits':{}}
    cycle=client.post('/api/mission-scenarios',json={**base,'activities':[
        {'id':'a','name':'A','duration_hours':1,'depends_on':['b']},
        {'id':'b','name':'B','duration_hours':1,'depends_on':['a']}]})
    assert cycle.status_code == 422 and 'cycle' in cycle.json()['detail']
    unknown=client.post('/api/mission-scenarios',json={**base,'activities':[
        {'id':'a','name':'A','duration_hours':1,'depends_on':['missing']}]})
    assert unknown.status_code == 422


def test_scenario_suitability_reference_must_match_site_and_body():
    p=_mission_profile('scenario-profile',[{'key':'slope','unit':'deg','minimum':0,'maximum':10,'required':True}])
    assessment=client.post('/api/suitability-assessments',json={'profile_id':'scenario-profile','profile_revision':1,'site_id':'site-a'})
    assert assessment.status_code == 201
    response=client.post('/api/mission-scenarios',json={
        'name':'mismatch','target_body':'Moon','site_id':'site-b','suitability_assessment_id':assessment.json()['id'],
        'activities':[{'id':'a','name':'A','duration_hours':1}]})
    assert response.status_code == 422


def test_stage19_qualitative_risk_unknown_and_attention():
    payload={'name':'risk test','target_body':'Mars','site_id':'risk-site','risks':[
      {'risk_id':'R1','title':'Unknown dust exposure','description':'Insufficient evidence','category':'environment',
       'likelihood':'unknown','impact':'major','uncertainty':'unknown','uncertainty_basis':'No measurement supplied',
       'mitigation':'Collect validated site evidence','evidence_refs':[]},
      {'risk_id':'R2','title':'Equipment damage','description':'Potential damage','category':'hardware',
       'likelihood':'likely','impact':'severe','uncertainty':'estimated','uncertainty_basis':'Preliminary engineering estimate',
       'mitigation':'Protective enclosure','evidence_refs':['manifest:example']}
    ]}
    r=client.post('/api/mission-risk-assessments',json=payload)
    assert r.status_code==201, r.text
    d=r.json()
    assert d['result']['overall_state']=='indeterminate'
    assert d['result']['items'][0]['state']=='indeterminate'
    assert d['result']['items'][1]['state']=='attention-required'
    assert 'probability' in d['result']['method']

def test_stage19_risk_snapshot_immutable_and_site_validation():
    base={'name':'linked risk','target_body':'Mars','site_id':'risk-site','risks':[
      {'risk_id':'R1','title':'Risk','description':'Desc','category':'ops','likelihood':'possible',
       'impact':'moderate','uncertainty':'inferred','uncertainty_basis':'Reasoned inference','mitigation':'Review','evidence_refs':[]}]}
    r=client.post('/api/mission-risk-assessments',json=base)
    assert r.status_code==201
    ident=r.json()['id']
    fetched=client.get(f'/api/mission-risk-assessments/{ident}')
    assert fetched.status_code==200
    assert fetched.json()['input_snapshot']==r.json()['input_snapshot']
    bad={**base,'scenario_id':'missing-scenario'}
    assert client.post('/api/mission-risk-assessments',json=bad).status_code==404

def test_stage19_rejects_duplicate_risk_ids_and_invalid_categories():
    base={'name':'bad risk','target_body':'Moon','site_id':'site','risks':[]}
    item={'risk_id':'R','title':'T','description':'D','category':'ops','likelihood':'rare','impact':'minor',
          'uncertainty':'measured','uncertainty_basis':'Lab measurement','mitigation':'','evidence_refs':[]}
    base['risks']=[item,item]
    assert client.post('/api/mission-risk-assessments',json=base).status_code==422
    base['risks']=[{**item,'risk_id':'R2','likelihood':'impossible'}]
    assert client.post('/api/mission-risk-assessments',json=base).status_code==422


def _stage20_risk_assessment(site='stage20-site'):
    payload={'name':'Stage20 review fixture','target_body':'Mars','site_id':site,'risks':[
      {'risk_id':'R-20','title':'Thermal degradation','description':'Potential equipment degradation.',
       'category':'thermal','likelihood':'possible','impact':'major','uncertainty':'estimated',
       'uncertainty_basis':'Engineering estimate pending validation','mitigation':'Thermal enclosure and qualification test.',
       'evidence_refs':[]}]}
    response=client.post('/api/mission-risk-assessments',json=payload)
    assert response.status_code==201,response.text
    return response.json()

def test_stage20_review_workflow_and_readiness_states():
    assessment=_stage20_risk_assessment()
    ident=assessment['id']
    status=client.get(f'/api/mission-readiness/{ident}').json()
    assert status['readiness_state']=='review-incomplete'
    review=client.post(f'/api/mission-risk-assessments/{ident}/reviews',json={
      'risk_id':'R-20','reviewer':'reviewer-a','decision':'action-required',
      'rationale':'Mitigation test evidence is not yet available.','mitigation_evidence_refs':[]})
    assert review.status_code==201,review.text
    assert client.get(f'/api/mission-readiness/{ident}').json()['readiness_state']=='open-actions'
    manifest=client.post('/api/manifests',json={'dataset_id':'stage20-proof','version':'1','sha256':'c'*64,
      'source_uri':'https://example.org/stage20-proof.tif'})
    assert manifest.status_code==201
    mid=manifest.json()['id']
    approved=client.post(f'/api/manifests/{mid}/review',json={'decision':'approved',
      'reason':'Source metadata and checksum reviewed.','reviewer':'data-reviewer'})
    assert approved.status_code==200,approved.text
    verified=client.post(f'/api/mission-risk-assessments/{ident}/reviews',json={
      'risk_id':'R-20','reviewer':'reviewer-b','decision':'mitigation-verified',
      'rationale':'Approved test report supports the mitigation closure decision.',
      'mitigation_evidence_refs':[f'manifest:{mid}']})
    assert verified.status_code==201,verified.text
    assert verified.json()['mitigation_evidence'][0]['sha256']=='c'*64
    final=client.get(f'/api/mission-readiness/{ident}').json()
    assert final['readiness_state']=='reviewed-mitigations-verified'
    assert final['operational_authorization']=='not-assessed'
    history=client.get(f'/api/mission-risk-assessments/{ident}/reviews').json()['items']
    assert len(history)==2

def test_stage20_mitigation_verification_rejects_unapproved_or_bad_evidence():
    assessment=_stage20_risk_assessment('stage20-evidence-site')
    ident=assessment['id']
    pending=client.post('/api/manifests',json={'dataset_id':'stage20-pending','version':'1','sha256':'d'*64,
      'source_uri':'https://example.org/pending.tif'})
    mid=pending.json()['id']
    payload={'risk_id':'R-20','reviewer':'reviewer','decision':'mitigation-verified',
      'rationale':'Attempt to close risk without approved evidence.','mitigation_evidence_refs':[f'manifest:{mid}']}
    assert client.post(f'/api/mission-risk-assessments/{ident}/reviews',json=payload).status_code==409
    payload['mitigation_evidence_refs']=['not-a-valid-reference']
    assert client.post(f'/api/mission-risk-assessments/{ident}/reviews',json=payload).status_code==422
    payload['mitigation_evidence_refs']=[]
    assert client.post(f'/api/mission-risk-assessments/{ident}/reviews',json=payload).status_code==422

def test_stage20_review_requires_existing_risk_and_valid_rationale():
    assessment=_stage20_risk_assessment('stage20-validation-site')
    ident=assessment['id']
    payload={'risk_id':'UNKNOWN','reviewer':'reviewer','decision':'acknowledged',
      'rationale':'This is a valid rationale.','mitigation_evidence_refs':[]}
    assert client.post(f'/api/mission-risk-assessments/{ident}/reviews',json=payload).status_code==404
    payload['risk_id']='R-20'; payload['rationale']='short'
    assert client.post(f'/api/mission-risk-assessments/{ident}/reviews',json=payload).status_code==422
