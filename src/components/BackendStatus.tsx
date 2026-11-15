import { useEffect, useState } from 'react';
import { Database, RefreshCw, Server, ShieldCheck } from 'lucide-react';
import { terrascanApi, type ApiHealth } from '../services/api';

export default function BackendStatus() {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(true);
  const check = async () => {
    setChecking(true); setError('');
    try { setHealth(await terrascanApi.health()); }
    catch (e) { setHealth(null); setError(e instanceof Error ? e.message : 'Backend unavailable'); }
    finally { setChecking(false); }
  };
  useEffect(() => { void check(); }, []);
  return <section className="panel backend-status-panel">
    <div className="panel-header"><div><div className="panel-kicker">STAGE 12 · SERVICE LAYER</div><h2>Backend connectivity</h2></div><Server size={19} className="muted-icon" /></div>
    <div className="backend-health-row"><span className={`status-dot ${health ? '' : 'status-dot-offline'}`} /><strong>{checking ? 'CHECKING CONNECTION' : health ? 'API CONNECTED' : 'API NOT CONNECTED'}</strong><button className="subtle-button" onClick={() => void check()} disabled={checking}><RefreshCw size={13}/> Refresh</button></div>
    {health ? <div className="backend-metrics"><div><Database size={15}/><span>SQLite database</span><strong>{health.database}</strong></div><div><ShieldCheck size={15}/><span>API version</span><strong>{health.version}</strong></div></div> : <p className="backend-help">{error || 'Start the FastAPI service to connect the local database.'} Run <code>cd backend && pip install -r requirements.txt && python run.py</code>, then refresh.</p>}
    <p className="backend-note">The database starts empty. Evidence registration is blocked unless its source manifest has been approved. The API does not calculate or invent scientific similarity scores.</p>
  </section>;
}
