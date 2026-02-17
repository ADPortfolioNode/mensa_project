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
import chromaStateManager from '../utils/chromaStateManager';

const ALL_GAMES_VALUE = '__all_games__';
const GAME_COLOR_SCHEMES = ['primary', 'success', 'warning', 'info', 'danger', 'secondary', 'dark'];

export default function Dashboard() {
  const API_BASE = getApiBase();
  // Use runtime-computed API base
  // eslint-disable-next-line no-console
  console.debug('API base:', API_BASE);
  const [ingestStatus, setIngestStatus] = useState('idle');
  const [ingestErrorMessage, setIngestErrorMessage] = useState('');
  const [ingestingGame, setIngestingGame] = useState(null);
  const [ingestStartTime, setIngestStartTime] = useState(null);
  const [trainStatus, setTrainStatus] = useState('idle');
  const [trainErrorMessage, setTrainErrorMessage] = useState('');
  const [trainProgress, setTrainProgress] = useState(0);
  const [trainStartTime, setTrainStartTime] = useState(null);
  const [games, setGames] = useState([]);
  const [gameContents, setGameContents] = useState({});
  const [gameContentsErrorMessage, setGameContentsErrorMessage] = useState('');
  const [experiments, setExperiments] = useState([]);
  const [experimentsErrorMessage, setExperimentsErrorMessage] = useState('');
  const [selectedGame, setSelectedGame] = useState('');
  const [forceReingest, setForceReingest] = useState(false);
  const [selectedTrainGame, setSelectedTrainGame] = useState('');
  const [selectedExperimentReadyGame, setSelectedExperimentReadyGame] = useState('');
  const [selectedTrainingExperimentId, setSelectedTrainingExperimentId] = useState('');
  const [expandedCard, setExpandedCard] = useState(null);
  const [summaryRefreshKey, setSummaryRefreshKey] = useState(0);
  const [allGamesProgress, setAllGamesProgress] = useState({});
  const [startupErrorMessage, setStartupErrorMessage] = useState('');
  const [startupStatus, setStartupStatus] = useState({
    status: 'unknown',
    progress: 0,
    total: 0,
    elapsed_s: 0,
  });

  useEffect(() => {
    if (
      ingestStatus !== 'in progress' ||
      selectedGame !== ALL_GAMES_VALUE ||
      !ingestingGame
    ) {
      return;
    }

    let cancelled = false;

    const pollCurrentGameProgress = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/ingest_progress?game=${ingestingGame}`);
        if (cancelled || !response?.data) return;

        const rowsFetched = Number(response.data.rows_fetched || 0);
        const totalRows = Number(response.data.total_rows || 0);
        const backendStatus = String(response.data.status || '').toLowerCase();
        const mappedStatus = backendStatus === 'completed'
          ? 'completed'
          : backendStatus === 'error'
            ? 'error'
            : backendStatus === 'ingesting'
              ? 'active'
              : 'pending';

        setAllGamesProgress((prev) => ({
          ...prev,
          [ingestingGame]: {
            ...(prev[ingestingGame] || {}),
            status: mappedStatus,
            rowsFetched,
            totalRows,
          },
        }));
      } catch {
        // keep existing progress state; transient poll failures are expected
      }
    };

    pollCurrentGameProgress();
    const interval = setInterval(pollCurrentGameProgress, 1000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [ingestStatus, selectedGame, ingestingGame, API_BASE]);
  
  // Training parameters
  const [trainParams, setTrainParams] = useState({
    testSize: 0.33,
    randomState: 42,
    nEstimators: 100,
    maxDepth: 10
  });

  useEffect(() => {
    async function fetchGamesAndContents() {
      try {
        const r = await axios.get(`${API_BASE}/api/games`);
        setGameContentsErrorMessage('');
        const gameList = r.data.games || [];
        setGames(gameList);
        setSelectedTrainGame((prev) => prev || gameList[0] || '');
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
        setGameContentsErrorMessage(e?.response?.data?.detail || e.message || 'Failed to fetch game contents.');
      }
    }
    fetchGamesAndContents();
  }, [API_BASE]);

  // Polling for experiments
  useEffect(() => {
    async function fetchExperiments() {
      try {
        const r = await axios.get(`${API_BASE}/api/experiments`);
        const experimentsPayload = Array.isArray(r.data)
          ? r.data
          : (Array.isArray(r.data?.experiments) ? r.data.experiments : []);
        setExperiments(experimentsPayload);
        setExperimentsErrorMessage('');
      } catch (e) {
        setExperimentsErrorMessage(e?.response?.data?.detail || e.message || 'Failed to fetch experiments.');
      }
    }
    fetchExperiments(); // Fetch immediately on mount

    const experimentPollInterval = setInterval(fetchExperiments, 5000); // Poll every 5 seconds

    return () => clearInterval(experimentPollInterval); // Clear interval on unmount
  }, [API_BASE]);

  useEffect(() => {
    let cancelled = false;

    const fetchStartupStatus = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/startup_status`);
        setStartupErrorMessage('');
        if (!cancelled && response?.data) {
          setStartupStatus({
            status: String(response.data.status || 'unknown').toLowerCase(),
            progress: Number(response.data.progress || 0),
            total: Number(response.data.total || 0),
            elapsed_s: Number(response.data.elapsed_s || 0),
          });
        }
      } catch {
        setStartupErrorMessage('Failed to refresh startup status.');
      }
    };

    fetchStartupStatus();
    const interval = setInterval(fetchStartupStatus, 5000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [API_BASE]);

  const startIngest = useCallback(async () => {
    if (!selectedGame) return;
    setIngestStatus('in progress');
    setIngestErrorMessage('');
    setIngestStartTime(Date.now());
    setExpandedCard('ingest');

    try {
      if (selectedGame === ALL_GAMES_VALUE) {
        setAllGamesProgress(
          games.reduce((acc, game) => {
            acc[game] = { status: 'pending', totalRows: 0, rowsFetched: 0 };
            return acc;
          }, {})
        );
        setIngestingGame(ALL_GAMES_VALUE);

        const gameTasks = games.map((game) => (async () => {
          setAllGamesProgress((prev) => ({
            ...prev,
            [game]: {
              ...(prev[game] || {}),
              status: 'active',
            },
          }));

          let pollCancelled = false;
          const pollCurrentGameProgress = async () => {
            try {
              const progressRes = await axios.get(`${API_BASE}/api/ingest_progress?game=${game}`);
              const progressData = progressRes?.data || {};
              if (pollCancelled) return;

              const rowsFetched = Number(progressData.rows_fetched || 0);
              const totalRows = Number(progressData.total_rows || 0);
              const backendStatus = String(progressData.status || '').toLowerCase();
              const mappedStatus = backendStatus === 'completed'
                ? 'completed'
                : backendStatus === 'error'
                  ? 'error'
                  : backendStatus === 'ingesting'
                    ? 'active'
                    : 'pending';

              setAllGamesProgress((prev) => ({
                ...prev,
                [game]: {
                  ...(prev[game] || {}),
                  status: mappedStatus,
                  rowsFetched,
                  totalRows,
                },
              }));
            } catch {
              // transient progress polling failures should not break ingestion
            }
          };

          const pollInterval = setInterval(pollCurrentGameProgress, 1000);
          await pollCurrentGameProgress();

          try {
            const response = await axios.post(`${API_BASE}/api/ingest`, { game, force: forceReingest });
            const normalizedIngestStatus = String(response?.data?.status || '').toLowerCase();
            const isIngestSuccess = normalizedIngestStatus === 'completed' || normalizedIngestStatus === 'success';

            if (!isIngestSuccess) {
              setAllGamesProgress((prev) => ({
                ...prev,
                [game]: {
                  ...(prev[game] || {}),
                  status: 'error',
                },
              }));

              return {
                game,
                status: 'error',
                message: response?.data?.message || 'Ingestion failed.',
              };
            }

            setAllGamesProgress((prev) => ({
              ...prev,
              [game]: {
                ...(prev[game] || {}),
                status: 'completed',
                rowsFetched: response.data.total || prev[game]?.rowsFetched || 0,
                totalRows: response.data.total || prev[game]?.totalRows || 0,
              },
            }));

            return {
              game,
              status: 'completed',
              message: '',
            };
          } catch (err) {
            console.error(`Error ingesting ${game}:`, err);

            setAllGamesProgress((prev) => ({
              ...prev,
              [game]: {
                ...(prev[game] || {}),
                status: 'error',
              },
            }));

            return {
              game,
              status: 'error',
              message: err?.response?.data?.message || err.message || 'Ingestion request failed.',
            };
          } finally {
            pollCancelled = true;
            clearInterval(pollInterval);

            try {
              const res = await axios.get(`${API_BASE}/api/games/${game}/summary`);
              const drawCount = res.data.draw_count;
              setGameContents((prev) => ({
                ...prev,
                [game]: drawCount,
              }));
              chromaStateManager.notifyCollectionUpdate(game, 0, drawCount);
              setSummaryRefreshKey((prev) => prev + 1);
              setAllGamesProgress((prev) => ({
                ...prev,
                [game]: {
                  ...(prev[game] || {}),
                  rowsFetched: drawCount,
                  totalRows: drawCount,
                },
              }));
            } catch {
              // ignore per-game summary refresh failures
            }
          }
        })());

        const results = await Promise.allSettled(gameTasks);
        const resolvedResults = results.map((result, index) => {
          if (result.status === 'fulfilled') return result.value;
          return {
            game: games[index],
            status: 'error',
            message: result.reason?.message || 'Ingestion task failed.',
          };
        });

        const failures = resolvedResults.filter((item) => item.status === 'error');
        setIngestingGame(null);
        setIngestStatus(failures.length > 0 ? 'error' : 'completed');

        if (failures.length > 0) {
          const failureMessage = failures
            .map((item) => `${item.game.toUpperCase()}: ${item.message}`)
            .join(' | ');
          setIngestErrorMessage(failureMessage);
        } else {
          setIngestErrorMessage('');
          setExpandedCard(null);
        }
      } else {
        setAllGamesProgress({});
        setIngestingGame(selectedGame);
        const response = await axios.post(`${API_BASE}/api/ingest`, { game: selectedGame, force: forceReingest });
        const normalizedIngestStatus = String(response?.data?.status || '').toLowerCase();
        const isIngestSuccess = normalizedIngestStatus === 'completed' || normalizedIngestStatus === 'success';

        if (isIngestSuccess) {
          setIngestStatus('completed');
          setIngestingGame(null);
          setIngestErrorMessage('');
          const res = await axios.get(`${API_BASE}/api/games/${selectedGame}/summary`);
          const drawCount = res.data.draw_count;
          setGameContents(prev => ({
            ...prev,
            [selectedGame]: drawCount
          }));
          chromaStateManager.notifyCollectionUpdate(selectedGame, response.data.added || 0, drawCount);
          setSummaryRefreshKey((prev) => prev + 1);
          setExpandedCard(null);
        } else {
          setIngestStatus('error');
          setIngestErrorMessage(response?.data?.message || `Ingestion failed for ${selectedGame.toUpperCase()}.`);
          setIngestingGame(null);
        }
      }
    } catch (e) {
      console.error("Error starting ingestion:", e);
      setIngestStatus('error');
      setIngestErrorMessage(e?.response?.data?.message || e.message || 'Failed to start ingestion.');
      setIngestingGame(null);
    }
  }, [selectedGame, games, API_BASE, forceReingest]);

  const handleIngestionComplete = useCallback((progress) => {
    if (progress.status === 'completed') {
      setIngestStatus('completed');
      setIngestErrorMessage('');
      setTimeout(() => setExpandedCard(null), 2000); // Auto-collapse after 2s
    } else if (progress.status === 'error') {
      setIngestStatus('error');
      setIngestErrorMessage(progress?.error || `Ingestion failed for ${selectedGame?.toUpperCase() || 'selected game'}.`);
    }
    setIngestingGame(null);
    
    // Refresh game contents
    if (selectedGame) {
      axios.get(`${API_BASE}/api/games/${selectedGame}/summary`)
        .then(res => {
          const drawCount = res.data.draw_count;
          setGameContents(prev => ({
            ...prev,
            [selectedGame]: drawCount
          }));
          chromaStateManager.notifyCollectionUpdate(selectedGame, progress.added || 0, drawCount);
          setSummaryRefreshKey((prev) => prev + 1);
        })
        .catch(e => console.error("Error refreshing game content:", e));
    }
  }, [selectedGame, API_BASE]);

  const totalStoredDraws = useMemo(
    () => Object.values(gameContents).reduce((sum, count) => sum + Number(count || 0), 0),
    [gameContents]
  );

  const selectedGameStoredDraws = useMemo(() => {
    if (!selectedGame || selectedGame === ALL_GAMES_VALUE) {
      return totalStoredDraws;
    }
    return Number(gameContents[selectedGame] || 0);
  }, [selectedGame, gameContents, totalStoredDraws]);

  const hasStoredDataForSelection = selectedGameStoredDraws > 0;

  const completedTrainingExperiments = useMemo(() => {
    return (experiments || [])
      .filter((exp) => {
        const expType = String(exp?.type || '').toLowerCase();
        const expStatus = String(exp?.status || '').toLowerCase();
        return expType === 'training' && (expStatus === 'completed' || expStatus === 'success');
      })
      .sort((a, b) => Number(b?.timestamp || 0) - Number(a?.timestamp || 0));
  }, [experiments]);

  const trainingReadyGames = useMemo(() => {
    return [...new Set(completedTrainingExperiments.map((exp) => exp.game).filter(Boolean))];
  }, [completedTrainingExperiments]);

  const experimentsForReadyGame = useMemo(() => {
    if (!selectedExperimentReadyGame) return [];
    return completedTrainingExperiments.filter((exp) => exp.game === selectedExperimentReadyGame);
  }, [completedTrainingExperiments, selectedExperimentReadyGame]);

  const selectedTrainingExperiment = useMemo(() => {
    if (!selectedTrainingExperimentId) return null;
    return experimentsForReadyGame.find((exp) => exp.experiment_id === selectedTrainingExperimentId) || null;
  }, [experimentsForReadyGame, selectedTrainingExperimentId]);

  useEffect(() => {
    if (!trainingReadyGames.length) {
      setSelectedExperimentReadyGame('');
      return;
    }

    if (!selectedExperimentReadyGame || !trainingReadyGames.includes(selectedExperimentReadyGame)) {
      setSelectedExperimentReadyGame(trainingReadyGames[0]);
    }
  }, [trainingReadyGames, selectedExperimentReadyGame]);

  useEffect(() => {
    if (!experimentsForReadyGame.length) {
      setSelectedTrainingExperimentId('');
      return;
    }

    const selectedStillExists = experimentsForReadyGame.some((exp) => exp.experiment_id === selectedTrainingExperimentId);
    if (!selectedStillExists) {
      setSelectedTrainingExperimentId(experimentsForReadyGame[0].experiment_id);
    }
  }, [experimentsForReadyGame, selectedTrainingExperimentId]);

  const selectedTrainGameStoredDraws = useMemo(
    () => Number(gameContents[selectedTrainGame] || 0),
    [gameContents, selectedTrainGame]
  );

  const effectiveIngestStatus = useMemo(() => {
    if (ingestStatus === 'in progress') {
      return ingestStatus;
    }

    if (hasStoredDataForSelection) {
      return 'completed';
    }

    if (ingestStatus === 'error' || ingestStatus === 'completed') {
      return ingestStatus;
    }

    return 'idle';
  }, [ingestStatus, hasStoredDataForSelection]);

  const startTrain = useCallback(async () => {
    if (effectiveIngestStatus !== 'completed' || !selectedTrainGame) {
      alert('Please complete data ingestion first and select a game.');
      return;
    }
    if (selectedTrainGameStoredDraws <= 0) {
      alert('Selected training game has no draws. Please run ingestion for that game first.');
      return;
    }
    setTrainStatus('in progress');
    setTrainErrorMessage('');
    setTrainProgress(0);
    setTrainStartTime(Date.now());
    setExpandedCard('train');
    
    const interval = setInterval(() => setTrainProgress(p => Math.min(p + 5, 95)), 2000);
    try {
      const response = await axios.post(`${API_BASE}/api/train`, { 
        game: selectedTrainGame,
        ...trainParams // Include training parameters
      });
      clearInterval(interval); // Clear interval regardless of outcome
      setTrainProgress(100);
      const normalizedTrainStatus = String(response?.data?.status || '').toLowerCase();
      const isTrainSuccess = normalizedTrainStatus === 'completed' || normalizedTrainStatus === 'success';

      if (isTrainSuccess) {
        setTrainStatus('completed');
        setTrainErrorMessage('');
        // Refresh experiments
        const r = await axios.get(`${API_BASE}/api/experiments`);
        const experimentsPayload = Array.isArray(r.data)
          ? r.data
          : (Array.isArray(r.data?.experiments) ? r.data.experiments : []);
        setExperiments(experimentsPayload);
        setExperimentsErrorMessage('');
        alert(`Training completed successfully for ${selectedTrainGame.toUpperCase()}! Experiment ID: ${response.data.experiment_id}, Score: ${response.data.score}`);
        setTimeout(() => setExpandedCard(null), 2000);
      } else {
        setTrainStatus('error');
        setTrainErrorMessage(response.data.error || response.data.message || 'Training failed.');
        alert(`Training failed: ${response.data.error || response.data.message}`);
      }
    } catch (e) {
      clearInterval(interval);
      setTrainStatus('error');
      setTrainProgress(0);
      setTrainErrorMessage(e?.response?.data?.detail || e.message || 'Training request failed.');
      alert(`Training failed due to an error: ${e.response?.data?.detail || e.message}`);
    }
  }, [effectiveIngestStatus, selectedTrainGame, selectedTrainGameStoredDraws, trainParams, API_BASE]);

  const isTrained = completedTrainingExperiments.length > 0;

  const getGameColorScheme = (gameName) => {
    const idx = games.findIndex((name) => name === gameName);
    if (idx < 0) return 'primary';
    return GAME_COLOR_SCHEMES[idx % GAME_COLOR_SCHEMES.length];
  };

  const getGameLabelColor = (scheme) => {
    switch (scheme) {
      case 'primary': return '#0d6efd';
      case 'success': return '#198754';
      case 'warning': return '#996500';
      case 'info': return '#0dcaf0';
      case 'danger': return '#dc3545';
      case 'secondary': return '#6c757d';
      case 'dark': return '#212529';
      default: return '#0d6efd';
    }
  };

  const getGameProgressFraction = useCallback((progressItem) => {
    if (!progressItem) return 0;

    if (progressItem.status === 'completed') {
      return 1;
    }

    const totalRows = Number(progressItem.totalRows || 0);
    const rowsFetched = Number(progressItem.rowsFetched || 0);

    if (totalRows > 0) {
      return Math.max(0, Math.min(rowsFetched / totalRows, 1));
    }

    if (progressItem.status === 'active') {
      return 0.5;
    }

    return 0;
  }, []);

  const allGamesOverallProgressCurrent = useMemo(() => {
    if (!games.length) return 0;
    return games.reduce((acc, game) => acc + getGameProgressFraction(allGamesProgress[game]), 0);
  }, [games, allGamesProgress, getGameProgressFraction]);

  const initializationDisplay = useMemo(() => {
    const status = startupStatus.status;
    if (status === 'completed') return 'Completed';
    if (status === 'ready') return 'Ready';
    if (status === 'ingesting') return 'In Progress';
    if (status === 'failed') return 'Failed';
    if (status === 'pending') return 'Pending';
    return 'Unknown';
  }, [startupStatus.status]);

  // Helper to determine if card should span 2 columns
  const getColSpan = (cardKey) => {
    return expandedCard === cardKey ? 'col-md-12' : 'col-md-6';
  };

  const renderCardErrorAlert = (title, message, className = 'mt-3 mb-0') => {
    if (!message) return null;
    return (
      <div className={`alert alert-danger ${className}`} role="alert">
        <strong>{title}:</strong> {message}
      </div>
    );
  };
  
  return (
    <div className="container-fluid">
      <div className="card mb-4">
        <div className="card-body">
          <h4 className="text-neon mb-2">Lottery Data Initialization</h4>
          <p className="mb-0 text-muted">
            Status: {initializationDisplay}
            {startupStatus.total > 0 ? ` (${startupStatus.progress} of ${startupStatus.total} games)` : ''}
          </p>
          {startupErrorMessage && (
            <p className="mb-0 mt-2 text-danger">Error: {startupErrorMessage}</p>
          )}
        </div>
      </div>
      <WorkflowSummary />
      <div className="row g-4 mb-4">
        <div className="col-12 col-lg-4">
          <div className="card h-100">
            <div className="card-body">
              <h4 className="text-neon mb-3">Mensa Concierge</h4>
              <p className="mb-2">
                Friendly, personable, and deeply technical support for Python, React, ChromaDB, and RAG workflows.
              </p>
              <p className="mb-0 text-muted">
                Use built-in tools for file management, internet search, and self diagnostics directly from chat.
              </p>
            </div>
          </div>
        </div>
        <div className="col-12 col-lg-8">
          <ExpandableCard
            title="Concierge Chat"
            neonBorder={true}
            metadata={{
              'Persona': 'Friendly Expert Developer',
              'Tools': 'Files, Search, Diagnostics',
              'Context': selectedGame ? selectedGame.toUpperCase() : 'All Games'
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'chat' : null)}
          >
            <ChatPanelRAG game={selectedGame} />
          </ExpandableCard>
        </div>
      </div>
      <div className="mb-4">
        <h4 className="text-neon">Workflow Status</h4>
        <div className="mb-2">
          <ProgressiveProgressBar
            current={effectiveIngestStatus === 'completed' ? 1 : effectiveIngestStatus === 'in progress' ? 0.5 : 0}
            total={1}
            status={effectiveIngestStatus === 'completed' ? 'completed' : effectiveIngestStatus === 'in progress' ? 'active' : effectiveIngestStatus === 'error' ? 'error' : 'idle'}
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
            isActive={effectiveIngestStatus === 'in progress'}
            metadata={selectedGame ? {
              'Selected Game': selectedGame.toUpperCase(),
              'Current Draws': `${selectedGame === ALL_GAMES_VALUE ? totalStoredDraws : Number(gameContents[selectedGame] || 0)} draws`,
              'Status': effectiveIngestStatus,
              'Force Reingest': forceReingest ? 'Enabled' : 'Disabled',
              ...(ingestErrorMessage ? { 'Error Message': ingestErrorMessage } : {}),
              'API Endpoint': `${API_BASE}/api/ingest`
            } : {}}
            statusBadge={
              <span className={`badge ${effectiveIngestStatus === 'completed' ? 'bg-success' : effectiveIngestStatus === 'in progress' ? 'bg-warning' : effectiveIngestStatus === 'error' ? 'bg-danger' : 'bg-secondary'}`}>
                {effectiveIngestStatus}
              </span>
            }
            onToggle={(expanded) => setExpandedCard(expanded ? 'ingest' : null)}
          >
            <p>Fetch and sync lottery data from NY Open Data.</p>
            <div className="mb-3">
              <label htmlFor="gameSelect" className="form-label text-neon">Select Game</label>
              <GameSelector games={games} onGameSelect={setSelectedGame} includeAllOption={true} allOptionValue={ALL_GAMES_VALUE} allOptionLabel="All Games" />
            </div>
            <div className="form-check mb-3">
              <input
                id="forceReingestToggle"
                type="checkbox"
                className="form-check-input"
                checked={forceReingest}
                onChange={(e) => setForceReingest(e.target.checked)}
                disabled={ingestStatus === 'in progress'}
              />
              <label className="form-check-label" htmlFor="forceReingestToggle">
                Force reingest (reload even when draws already exist)
              </label>
            </div>
            {selectedGame && (
              <div className="alert alert-info">
                {selectedGame === ALL_GAMES_VALUE ? (
                  <><strong>ALL GAMES</strong>: Run ingestion sequentially for every available game</>
                ) : (
                  <><strong>{selectedGame.toUpperCase()}</strong>: {gameContents[selectedGame] || 0} draws currently stored</>
                )}
              </div>
            )}
            <button 
              className="btn btn-primary me-2" 
              onClick={startIngest} 
              disabled={ingestStatus === 'in progress' || !selectedGame}
            >
              {ingestStatus === 'in progress' ? 'Ingesting...' : 'Run Ingest'}
            </button>
            {renderCardErrorAlert('Ingestion Error', ingestErrorMessage, 'mt-3 mb-0')}
            
            {/* Ingestion Progress Panel */}
            {selectedGame !== ALL_GAMES_VALUE && (
              <IngestionProgressPanel 
                game={ingestingGame}
                isActive={ingestStatus === 'in progress'}
                onComplete={handleIngestionComplete}
              />
            )}

            {selectedGame === ALL_GAMES_VALUE && Object.keys(allGamesProgress).length > 0 && (
              <div className="mt-3">
                <h6 className="mb-2">All Games Progress</h6>
                <ProgressiveProgressBar
                  current={allGamesOverallProgressCurrent}
                  total={games.length || 1}
                  status={ingestStatus === 'error' ? 'error' : ingestStatus === 'completed' ? 'completed' : 'active'}
                  label="Overall All Games Ingestion"
                  showMetadata={true}
                  startTime={ingestStartTime}
                  colorScheme="success"
                />
                {games.map((game) => {
                  const gameProgress = allGamesProgress[game] || { status: 'pending', totalRows: 0, rowsFetched: 0 };
                  const gameColorScheme = getGameColorScheme(game);
                  const progressStatus = gameProgress.status === 'completed'
                    ? 'completed'
                    : gameProgress.status === 'error'
                      ? 'error'
                      : gameProgress.status === 'active'
                        ? 'active'
                        : 'idle';
                  const hasRowProgress = Number(gameProgress.totalRows) > 0;
                  const progressCurrent = hasRowProgress
                    ? Number(gameProgress.rowsFetched || 0)
                    : getGameProgressFraction(gameProgress);
                  const progressTotal = hasRowProgress ? Number(gameProgress.totalRows) : 1;

                  return (
                    <ProgressiveProgressBar
                      key={game}
                      current={progressCurrent}
                      total={progressTotal}
                      status={progressStatus}
                      label={`Ingest ${game.toUpperCase()}${gameProgress.totalRows ? ` (${gameProgress.totalRows.toLocaleString()} draws)` : ''}`}
                      labelColor={getGameLabelColor(gameColorScheme)}
                      showMetadata={true}
                      startTime={ingestStartTime}
                      colorScheme={gameColorScheme}
                    />
                  );
                })}
              </div>
            )}
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
              'Ready Games': trainingReadyGames.length,
              ...(selectedTrainingExperiment ? { 'Selected Experiment': selectedTrainingExperiment.experiment_id } : {}),
              'Status': trainStatus,
              ...(trainErrorMessage ? { 'Error Message': trainErrorMessage } : {})
            }}
            statusBadge={
              <span className={`badge ${trainStatus === 'completed' ? 'bg-success' : trainStatus === 'in progress' ? 'bg-warning' : trainStatus === 'error' ? 'bg-danger' : 'bg-secondary'}`}>
                {trainStatus}
              </span>
            }
            onToggle={(expanded) => setExpandedCard(expanded ? 'train' : null)}
          >
            <p>Train machine learning model on lottery draw history.</p>

            <div className="mb-3">
              <label htmlFor="trainGameSelect" className="form-label text-neon">Game for Training</label>
              <select
                id="trainGameSelect"
                className="form-select"
                value={selectedTrainGame}
                onChange={(e) => setSelectedTrainGame(e.target.value)}
                disabled={trainStatus === 'in progress'}
              >
                <option value="">Select game</option>
                {games.map((game) => (
                  <option key={game} value={game}>{game.toUpperCase()}</option>
                ))}
              </select>
            </div>

            <div className="mb-3">
              <label htmlFor="readyGamesSelect" className="form-label text-neon">Games Ready for Experiments</label>
              <select
                id="readyGamesSelect"
                className="form-select"
                value={selectedExperimentReadyGame}
                onChange={(e) => setSelectedExperimentReadyGame(e.target.value)}
                disabled={trainStatus === 'in progress' || trainingReadyGames.length === 0}
              >
                <option value="">Select ready game</option>
                {trainingReadyGames.map((game) => (
                  <option key={game} value={game}>{game.toUpperCase()}</option>
                ))}
              </select>
            </div>

            <div className="mb-3">
              <label htmlFor="trainingExperimentSelect" className="form-label text-neon">Completed Training Experiments</label>
              <select
                id="trainingExperimentSelect"
                className="form-select"
                value={selectedTrainingExperimentId}
                onChange={(e) => setSelectedTrainingExperimentId(e.target.value)}
                disabled={trainStatus === 'in progress' || experimentsForReadyGame.length === 0}
              >
                <option value="">Select experiment</option>
                {experimentsForReadyGame.map((exp) => (
                  <option key={exp.experiment_id} value={exp.experiment_id}>
                    {`${exp.experiment_id} | Score: ${Number(exp.score || 0).toFixed(4)} | ${new Date(exp.timestamp).toLocaleString()}`}
                  </option>
                ))}
              </select>
            </div>

            {selectedTrainingExperiment && (
              <div className="alert alert-info mb-3">
                <strong>Experiment Description:</strong>{' '}
                {selectedTrainingExperiment.description || 'No description available for this experiment.'}
              </div>
            )}
            
            {/* Training Parameters */}
            <div className="mb-3 training-params-panel">
              <h6 className="mb-2">Training Parameters</h6>
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
              disabled={trainStatus === 'in progress' || effectiveIngestStatus !== 'completed' || !selectedTrainGame || selectedTrainGameStoredDraws <= 0}
            >
              {trainStatus === 'in progress' ? 'Training...' : 'Start Training'}
            </button>
            {renderCardErrorAlert('Training Error', trainErrorMessage, 'mt-3 mb-0')}
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
              'Total Draws': Object.values(gameContents).reduce((a, b) => a + b, 0),
              ...(gameContentsErrorMessage ? { 'Error Message': gameContentsErrorMessage } : {})
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'games' : null)}
          >
            {renderCardErrorAlert('Game Content Error', gameContentsErrorMessage, 'mb-3')}
            <GameSummaryPanel games={games} refreshKey={summaryRefreshKey} initialSummaries={gameContents} />
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
              'Last Updated': new Date().toLocaleString(),
              ...(experimentsErrorMessage ? { 'Error Message': experimentsErrorMessage } : {})
            }}
            onToggle={(expanded) => setExpandedCard(expanded ? 'experiments' : null)}
          >
            {renderCardErrorAlert('Experiments Error', experimentsErrorMessage, 'mb-3')}
            <ExperimentsPanel experiments={experiments} />
          </ExpandableCard>
        </div>
      </div>
    </div>
  );
}
