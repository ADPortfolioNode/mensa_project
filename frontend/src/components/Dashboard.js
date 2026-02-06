import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import getApiBase from '../utils/apiBase';
import PredictionPanel from './PredictionPanel';
import ChatPanelRAG from './ChatPanelRAG';
import WorkflowSummary from './WorkflowSummary';
import ExperimentsPanel from './ExperimentsPanel';
import GameSummaryPanel from './GameSummaryPanel';
import ChromaStatusPanel from './ChromaStatusPanel';
import GameSelector from './GameSelector';
import IngestionProgressPanel from './IngestionProgressPanel';
import ExpandableCard from './ExpandableCard';
import ProgressiveProgressBar from './ProgressiveProgressBar';

export default function Dashboard() {
  const API_BASE = getApiBase();
  // Use runtime-computed API base
  // eslint-disable-next-line no-console
  console.debug('API base:', API_BASE);
  const [ingestStatus, setIngestStatus] = useState('idle');
  const [ingestingGame, setIngestingGame] = useState(null);
  const [ingestStartTime, setIngestStartTime] = useState(null);
  const [trainStatus, setTrainStatus] = useState('idle');
  const [trainProgress, setTrainProgress] = useState(0);
  const [trainStartTime, setTrainStartTime] = useState(null);
  const [games, setGames] = useState([]);
  const [gameContents, setGameContents] = useState({});
  const [experiments, setExperiments] = useState([]);
  const [selectedGame, setSelectedGame] = useState('');
  const [expandedCard, setExpandedCard] = useState(null);
  
  // Training parameters
  const [trainParams, setTrainParams] = useState({
    testSize: 0.33,
    randomState: 42,
    nEstimators: 100,
    maxDepth: 10
  });

  // Memoize the gameContentsWithMeta calculation
  const gameContentsMeta = useMemo(() => {
    return Object.entries(gameContents).reduce((acc, [game, count]) => {
      acc[game] = {
        draws: count,
        status: count > 0 ? 'Ready' : 'Empty',
        lastFetch: new Date().toLocaleString()
      };
      return acc;
    }, {});
  }, [gameContents]);

  useEffect(() => {
    async function fetchGamesAndContents() {
      try {
        const r = await axios.get(`${API_BASE}/api/games`);
        const gameList = r.data.games || [];
        setGames(gameList);
        // Fetch draw counts for each game
        const contents = {};
        for (const game of gameList) {
          try {
            const res = await axios.get(`${API_BASE}/api/games/${game}/summary`);
            contents[game] = res.data.draw_count;
          } catch {
            contents[game] = 0;
          }
        }
        setGameContents(contents);
        // If no games or all draw counts are zero, prompt for auto-ingestion
        if (gameList.length === 0 || Object.values(contents).every(c => c === 0)) {
          if (window.confirm('No game data found. Would you like to auto-ingest the full spread?')) {
            for (const game of gameList) {
              await axios.post(`${API_BASE}/api/ingest`, { game });
            }
            window.location.reload();
          }
        }
      } catch (e) {
        // ignore
      }
    }
    fetchGamesAndContents();
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

  const startIngest = useCallback(async () => {
    if (!selectedGame) return;
    setIngestStatus('in progress');
    setIngestingGame(selectedGame);
    setIngestStartTime(Date.now());
    setExpandedCard('ingest');

    try {
      // Initiate ingestion - backend will handle progress async
      const response = await axios.post(`${API_BASE}/api/ingest`, { game: selectedGame });
      
      if (response.data.status === 'completed') {
        setIngestStatus('completed');
        setIngestingGame(null);
        // Refresh game contents to show updated counts
        const res = await axios.get(`${API_BASE}/api/games/${selectedGame}/summary`);
        setGameContents(prev => ({
          ...prev,
          [selectedGame]: res.data.draw_count
        }));
        setExpandedCard(null);
      } else {
        setIngestStatus('error');
        setIngestingGame(null);
      }
    } catch (e) {
      console.error("Error starting ingestion:", e);
      setIngestStatus('error');
      setIngestingGame(null);
    }
  }, [selectedGame, API_BASE]);

  const handleIngestionComplete = useCallback((progress) => {
    if (progress.status === 'completed') {
      setIngestStatus('completed');
      setTimeout(() => setExpandedCard(null), 2000); // Auto-collapse after 2s
    } else if (progress.status === 'error') {
      setIngestStatus('error');
    }
    setIngestingGame(null);
    
    // Refresh game contents
    if (selectedGame) {
      axios.get(`${API_BASE}/api/games/${selectedGame}/summary`)
        .then(res => {
          setGameContents(prev => ({
            ...prev,
            [selectedGame]: res.data.draw_count
          }));
        })
        .catch(e => console.error("Error refreshing game content:", e));
    }
  }, [selectedGame, API_BASE]);

  const startTrain = useCallback(async () => {
    if (ingestStatus !== 'completed' || !selectedGame) {
      alert('Please complete data ingestion first and select a game.');
      return;
    }
    setTrainStatus('in progress');
    setTrainProgress(0);
    setTrainStartTime(Date.now());
    setExpandedCard('train');
    
    const interval = setInterval(() => setTrainProgress(p => Math.min(p + 5, 95)), 2000);
    try {
      const response = await axios.post(`${API_BASE}/api/train`, { 
        game: selectedGame,
        ...trainParams // Include training parameters
      });
      clearInterval(interval); // Clear interval regardless of outcome
      setTrainProgress(100);

      if (response.data.status === 'COMPLETED') {
        setTrainStatus('completed');
        // Refresh experiments
        const r = await axios.get(`${API_BASE}/api/experiments`);
        setExperiments(r.data.experiments || []);
        alert(`Training completed successfully! Experiment ID: ${response.data.experiment_id}, Score: ${response.data.score}`);
        setTimeout(() => setExpandedCard(null), 2000);
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
  }, [ingestStatus, selectedGame, trainParams, API_BASE]);

  const isTrained = experiments.length > 0;

  // Helper to determine if card should span 2 columns
  const getColSpan = (cardKey) => {
    return expandedCard === cardKey ? 'col-md-12' : 'col-md-6';
  };
  
  return (
    <div className="container-fluid">
      <WorkflowSummary />
      <div className="mb-4">
        <h4 className="text-neon">Workflow Status</h4>
        <div className="mb-2">
          <ProgressiveProgressBar
            current={ingestStatus === 'completed' ? 1 : ingestStatus === 'in progress' ? 0.5 : 0}
            total={1}
            status={ingestStatus === 'completed' ? 'completed' : ingestStatus === 'in progress' ? 'active' : 'idle'}
            label="1. Ingest Data"
            showMetadata={false}
          />
        </div>
        <div className="mb-2">
          <ProgressiveProgressBar
            current={trainProgress}
            total={100}
            status={trainStatus === 'completed' ? 'completed' : trainStatus === 'in progress' ? 'active' : 'idle'}
            label="2. Train Model"
            showMetadata={trainStatus === 'in progress'}
            startTime={trainStartTime}
          />
        </div>
        <div className="mb-2">
          <ProgressiveProgressBar
            current={isTrained ? 1 : 0}
            total={1}
            status={isTrained ? 'completed' : 'idle'}
            label="3. Make Predictions"
            showMetadata={false}
          />
        </div>
      </div>

      <div className="row g-4">
        {/* Data Ingestion Card */}
        <div className={`col-12 ${getColSpan('ingest')}`}>
          <ExpandableCard
            title="Data Ingestion"
            neonBorder={true}
            isActive={ingestStatus === 'in progress'}
            metadata={selectedGame ? {
              'Selected Game': selectedGame.toUpperCase(),
              'Current Draws': `${gameContents[selectedGame] || 0} draws`,
              'Status': ingestStatus,
              'API Endpoint': `${API_BASE}/api/ingest`
            } : {}}
            statusBadge={
              <span className={`badge ${ingestStatus === 'completed' ? 'bg-success' : ingestStatus === 'in progress' ? 'bg-warning' : ingestStatus === 'error' ? 'bg-danger' : 'bg-secondary'}`}>
                {ingestStatus}
              </span>
            }
            onToggle={(expanded) => setExpandedCard(expanded ? 'ingest' : null)}
          >
            <p>Fetch and sync lottery data from NY Open Data.</p>
            <div className="mb-3">
              <label htmlFor="gameSelect" className="form-label text-neon">Select Game</label>
              <GameSelector games={games} onGameSelect={setSelectedGame} />
            </div>
            {selectedGame && (
              <div className="alert alert-info">
                <strong>{selectedGame.toUpperCase()}</strong>: {gameContents[selectedGame] || 0} draws currently stored
              </div>
            )}
            <button 
              className="btn btn-primary me-2" 
              onClick={startIngest} 
              disabled={ingestStatus === 'in progress' || !selectedGame}
            >
              {ingestStatus === 'in progress' ? 'Ingesting...' : 'Run Ingest'}
            </button>
            
            {/* Ingestion Progress Panel */}
            <IngestionProgressPanel 
              game={ingestingGame}
              isActive={ingestStatus === 'in progress'}
              onComplete={handleIngestionComplete}
            />
          </ExpandableCard>
        </div>

        {/* Model Training Card */}
        <div className={`col-12 ${getColSpan('train')}`}>
          <ExpandableCard
            title="Model Training"
            neonBorder={true}
            isActive={trainStatus === 'in progress'}
            metadata={{
              'Model Type': 'Random Forest Classifier',
              'Test Size': `${(trainParams.testSize * 100).toFixed(0)}%`,
              'N Estimators': trainParams.nEstimators,
              'Max Depth': trainParams.maxDepth,
              'Random State': trainParams.randomState,
              'Status': trainStatus
            }}
            statusBadge={
              <span className={`badge ${trainStatus === 'completed' ? 'bg-success' : trainStatus === 'in progress' ? 'bg-warning' : trainStatus === 'error' ? 'bg-danger' : 'bg-secondary'}`}>
                {trainStatus}
              </span>
            }
            onToggle={(expanded) => setExpandedCard(expanded ? 'train' : null)}
          >
            <p>Train machine learning model on lottery draw history.</p>
            
            {/* Training Parameters */}
            <div className="mb-3" style={{
              background: '#f8f9fa',
              padding: '12px',
              borderRadius: '6px',
              border: '1px solid #dee2e6'
            }}>
              <h6 style={{ marginBottom: '10px' }}>Training Parameters</h6>
              <div className="row g-2">
                <div className="col-md-6">
                  <label className="form-label small">Test Size (%)</label>
                  <input 
                    type="number" 
                    className="form-control form-control-sm"
                    value={trainParams.testSize * 100}
                    onChange={(e) => setTrainParams({...trainParams, testSize: parseFloat(e.target.value) / 100})}
                    min="10"
                    max="50"
                    step="5"
                    disabled={trainStatus === 'in progress'}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label small">N Estimators</label>
                  <input 
                    type="number" 
                    className="form-control form-control-sm"
                    value={trainParams.nEstimators}
                    onChange={(e) => setTrainParams({...trainParams, nEstimators: parseInt(e.target.value)})}
                    min="50"
                    max="500"
                    step="50"
                    disabled={trainStatus === 'in progress'}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label small">Max Depth</label>
                  <input 
                    type="number" 
                    className="form-control form-control-sm"
                    value={trainParams.maxDepth}
                    onChange={(e) => setTrainParams({...trainParams, maxDepth: parseInt(e.target.value)})}
                    min="5"
                    max="50"
                    step="5"
                    disabled={trainStatus === 'in progress'}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label small">Random State</label>
                  <input 
                    type="number" 
                    className="form-control form-control-sm"
                    value={trainParams.randomState}
                    onChange={(e) => setTrainParams({...trainParams, randomState: parseInt(e.target.value)})}
                    disabled={trainStatus === 'in progress'}
                  />
                </div>
              </div>
            </div>

            {trainStatus === 'in progress' && (
              <div className="mb-3">
                <ProgressiveProgressBar
                  current={trainProgress}
                  total={100}
                  status="active"
                  label="Training Progress"
                  showMetadata={true}
                  startTime={trainStartTime}
                  colorScheme="success"
                />
              </div>
            )}
            <button 
              className="btn btn-success" 
              onClick={startTrain} 
              disabled={trainStatus === 'in progress' || ingestStatus !== 'completed' || !selectedGame}
            >
              {trainStatus === 'in progress' ? 'Training...' : 'Start Training'}
            </button>
          </ExpandableCard>
        </div>

        {/* Prediction Panel */}
        <div className="col-12 col-md-6">
          <ExpandableCard
            title="Predictions"
            neonBorder={true}
            metadata={{
              'Status': isTrained ? 'Model Ready' : 'Awaiting Training',
              'Experiments': experiments.length
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'predict' : null)}
          >
            <PredictionPanel games={games} disabled={!isTrained} />
          </ExpandableCard>
        </div>

        {/* Game Summary */}
        <div className="col-12 col-md-6">
          <ExpandableCard
            title="Game Contents"
            neonBorder={true}
            metadata={{
              'Total Games': games.length,
              'Total Draws': Object.values(gameContents).reduce((a, b) => a + b, 0)
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'games' : null)}
          >
            <GameSummaryPanel games={games} />
          </ExpandableCard>
        </div>

        {/* Chat Agent */}
        <div className="col-12 col-md-6">
          <ExpandableCard
            title="Chat Agent (RAG)"
            neonBorder={true}
            metadata={{
              'Context': selectedGame ? selectedGame.toUpperCase() : 'All Games',
              'Backend': 'Gemini + ChromaDB'
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'chat' : null)}
          >
            <ChatPanelRAG game={selectedGame} />
          </ExpandableCard>
        </div>

        {/* ChromaDB Status */}
        <div className="col-12 col-md-6">
          <ExpandableCard
            title="ChromaDB Collections"
            neonBorder={true}
            metadata={{
              'Host': 'mensa_chroma',
              'Port': '8000'
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'chroma' : null)}
          >
            <ChromaStatusPanel />
          </ExpandableCard>
        </div>

        {/* Experiments */}
        <div className="col-12">
          <ExpandableCard
            title="Training Experiments"
            neonBorder={true}
            metadata={{
              'Total Experiments': experiments.length,
              'Last Updated': new Date().toLocaleString()
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'experiments' : null)}
          >
            <ExperimentsPanel experiments={experiments} />
          </ExpandableCard>
        </div>
      </div>
    </div>
  );
}
