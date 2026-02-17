import React, { useEffect, useState } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';

export default function StatusPanel({ status: initial = {} }) {
  // Normalize API base: trim, strip trailing slashes, and ensure scheme when provided
  function normalizeApiBase(raw) {
    const v = (raw || '').toString().trim().replace(/\/+$/, '');
    if (!v) return '';
    if (!/^https?:\/\//i.test(v)) {
      return `http://${v}`;
    }
    return v;
  }

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
  }, []);

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
            const pct = info.progress ?? 0;
            return (
              <div key={id} className="mb-2">
                <div className="d-flex justify-content-between">
                  <small className="text-monospace">{id}</small>
                  <small>{pct}%</small>
                </div>
                <div className="status-panel-progress-wrap">
                  <progress className="status-panel-progress" value={pct} max="100" aria-valuenow={pct} aria-valuemin="0" aria-valuemax="100" />
                </div>
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