import React, { useEffect, useState } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';
import ProgressiveProgressBar from './ProgressiveProgressBar';

export default function StatusPanel({ status: initial = {} }) {
  const API_BASE = getApiBase();
  const [status, setStatus] = useState(initial);

  useEffect(() => {
    async function load() {
      try {
        const r = await axios.get(`${API_BASE}/clones`);
        setStatus(r.data.clones || {});
      } catch (e) {
        // ignore
      }
    }
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [API_BASE]);

  return (
    <div className="card p-3">
      <h5>Agents</h5>
      <div>Active clones: {status.active_clones ?? 0}</div>
      <div>Max clones: {status.max_clones ?? 'N/A'}</div>
      <div className="mt-2">
        <strong>Clones:</strong>
        <div className="small">
          {(status.clones || []).length === 0 && <div>No active clones</div>}
          {(status.clones || []).map(id => {
            const info = (status.clone_info && status.clone_info[id]) || {};
            const pct = Number(info.progress ?? 0);
            return (
              <div key={id} className="mb-2">
                <ProgressiveProgressBar
                  current={pct}
                  total={100}
                  status={pct >= 100 ? 'completed' : pct > 0 ? 'active' : 'idle'}
                  label={id}
                  showMetadata={false}
                  colorScheme="info"
                />
                <div className="small text-muted mt-1">
                  {(info.steps || []).slice(-3).map((s, idx) => (
                    <div key={idx}>{s.step}: {s.status}</div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}