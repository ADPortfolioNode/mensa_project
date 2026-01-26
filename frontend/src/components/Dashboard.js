import React, { useState, useEffect } from 'react';
import axios from 'axios';
import PredictionPanel from './PredictionPanel';
import ChatPanel from './ChatPanel';
import WorkflowSummary from './WorkflowSummary';
import ExperimentsPanel from './ExperimentsPanel';
import GameSummaryPanel from './GameSummaryPanel';
import ChromaStatusPanel from './ChromaStatusPanel';
import GameSelector from './GameSelector';

export default function Dashboard() {
  // Normalize API base: trim, strip trailing slashes, and ensure scheme when provided
  function normalizeApiBase(raw) {
    const v = (raw || '').toString().trim().replace(/\/+$/, '');
    if (!v) return '';
    // If missing http/https, assume http:// for convenience
    if (!/^https?:\/\//i.test(v)) {
      return `http://${v}`;
    }
    return v;
  }

  const API_BASE = normalizeApiBase(process.env.REACT_APP_API_BASE);
  // runtime validation: warn if the provided API base does not parse as a URL
  try {
    if (process.env.REACT_APP_API_BASE && API_BASE) {
      // URL constructor will throw for invalid values
      // eslint-disable-next-line no-unused-vars
      const _u = new URL(API_BASE);
    }
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("REACT_APP_API_BASE looks malformed:", process.env.REACT_APP_API_BASE, "normalized:", API_BASE);
  }
  const [ingestStatus, setIngestStatus] = useState('idle');
  const [trainStatus, setTrainStatus] = useState('idle');
  const [trainProgress, setTrainProgress] = useState(0);
  const [games, setGames] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [selectedGame, setSelectedGame] = useState('');

  useEffect(() => {
    async function fetchGames() {
      try {
        const r = await axios.get(`${API_BASE}/api/games`);
        setGames(r.data.games || []);
      } catch (e) {
        // ignore
      }
    }
    fetchGames();
  }, [API_BASE]);

  // Polling for experiments
  useEffect(() => {
    async function fetchExperiments() {
      try {
        const r = await axios.get(`${API_BASE}/api/experiments`);
        setExperiments(r.data.experiments || []);
      } catch (e) {
        // ignore
      }
    }
    fetchExperiments(); // Fetch immediately on mount

    const experimentPollInterval = setInterval(fetchExperiments, 5000); // Poll every 5 seconds

    return () => clearInterval(experimentPollInterval); // Clear interval on unmount
  }, [API_BASE]);

  const startIngest = async () => {
    if (!selectedGame) return;
    setIngestStatus('in progress');

    try {
        const response = await axios.post(`${API_BASE}/api/ingest`, { game: selectedGame });
        if (response.data.status === 'success') {
            setIngestStatus('completed');
            alert(`Ingestion completed! Added ${response.data.added} documents.`);
            // After successful ingest, we could automatically refresh other components,
            // but for now an alert is sufficient to signal completion.
        } else {
            setIngestStatus('error');
            alert(`Ingestion failed: ${response.data.message}`);
        }
    } catch (e) {
      console.error("Error starting ingestion:", e);
      setIngestStatus('error');
      alert(`Ingestion failed due to an error: ${e.response?.data?.detail || e.message}`);
    }
  };

  const startTrain = async () => {
    if (ingestStatus !== 'completed' || !selectedGame) {
      alert('Please complete data ingestion first and select a game.');
      return;
    }
    setTrainStatus('in progress');
    setTrainProgress(0);
    const interval = setInterval(() => setTrainProgress(p => Math.min(p + 5, 95)), 2000);
    try {
      const response = await axios.post(`${API_BASE}/api/train`, { game: selectedGame });
      clearInterval(interval); // Clear interval regardless of outcome
      setTrainProgress(100);

      if (response.data.status === 'COMPLETED') {
        setTrainStatus('completed');
        // Refresh experiments
        const r = await axios.get(`${API_BASE}/api/experiments`);
        setExperiments(r.data.experiments || []);
        alert(`Training completed successfully! Experiment ID: ${response.data.experiment_id}, Score: ${response.data.score}`);
      } else {
        setTrainStatus('error');
        alert(`Training failed: ${response.data.error || response.data.message}`);
      }
    } catch (e) {
      clearInterval(interval);
      setTrainStatus('error');
      setTrainProgress(0);
      alert(`Training failed due to an error: ${e.response?.data?.detail || e.message}`);
    }
  };

  const isTrained = experiments.length > 0;
  
  return (
    <div>
      <WorkflowSummary />
      <div className="mb-4">
        <h4>Workflow Status</h4>
        <div className="mb-2">
          <div className="d-flex justify-content-between">
            <span>1. Ingest Data</span>
            <span className={`badge ${ingestStatus === 'completed' ? 'bg-success' : ingestStatus === 'in progress' ? 'bg-warning' : ingestStatus === 'error' ? 'bg-danger' : 'bg-secondary'}`}>{ingestStatus}</span>
          </div>
          {ingestStatus === 'in progress' && (
            <div className="progress mt-2" style={{height: '10px'}}>
              <div className="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style={{width: `100%`}}></div>
            </div>
          )}
        </div>
        <div className="mb-2">
          <div className="d-flex justify-content-between">
            <span>2. Train Model</span>
            <span className={`badge ${trainStatus === 'completed' ? 'bg-success' : trainStatus === 'in progress' ? 'bg-warning' : trainStatus === 'error' ? 'bg-danger' : 'bg-secondary'}`}>{trainStatus}</span>
          </div>
          {trainStatus === 'in progress' && (
            <div className="d-flex align-items-center mt-2">
              <div className="spinner-border spinner-border-sm me-2" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <span>Training in progress...</span>
            </div>
          )}
        </div>
        <div className="d-flex justify-content-between">
          <span>3. Make Predictions</span>
          <span className={`badge ${isTrained ? 'bg-success' : 'bg-secondary'}`}>{isTrained ? 'ready' : 'pending'}</span>
        </div>
      </div>

      <div className="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
        <div className="col">
          <div className="card p-3 mb-3 h-100">
            <h5>Data Ingestion</h5>
            <p>Fetch and sync lottery data.</p>
            <div className="mb-3">
                <label htmlFor="gameSelect" className="form-label">Select Game</label>
                <GameSelector games={games} onGameSelect={setSelectedGame} />
            </div>
            {selectedGame && <h2>Selected Game: {selectedGame}</h2>}
            <button className="btn btn-primary me-2" onClick={startIngest} disabled={ingestStatus === 'in progress' || !selectedGame}>Run Ingest</button>
            <button className="btn btn-secondary mt-2" onClick={startTrain} disabled={trainStatus === 'in progress' || ingestStatus !== 'completed' || !selectedGame}>Run Train</button>
          </div>
        </div>

        <div className="col">
          <PredictionPanel games={games} disabled={!isTrained} />
        </div>

        <div className="col">
          <GameSummaryPanel games={games} />
        </div>

        <div className="col">
            <div className="card h-100">
                <div className="card-header">
                    <h5>Chat Agent</h5>
                </div>
                <div className="card-body">
                    <ChatPanel />
                </div>
            </div>
        </div>

      </div>

      <div className="row mt-4">
        <div className="col">
          <ExperimentsPanel experiments={experiments} />
        </div>
        <div className="col">
            <ChromaStatusPanel />
        </div>
      </div>
    </div>
  );
}
