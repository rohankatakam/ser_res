/**
 * Settings Modal - Configure API keys and load algorithm/dataset
 */

import { useState, useEffect } from 'react';
import { 
  listAlgorithms, 
  listDatasets, 
  validateCompatibility,
  loadConfiguration,
  getConfigStatus,
  getEmbeddingStatus,
  getJudgeConfig,
  updateJudgeConfig
} from '../api';

export default function SettingsModal({ 
  isOpen, 
  onClose, 
  geminiKey, 
  onGeminiKeyChange,
  openaiKey,
  onOpenaiKeyChange,
  anthropicKey,
  onAnthropicKeyChange,
  onConfigLoaded 
}) {
  const [algorithms, setAlgorithms] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [compatibility, setCompatibility] = useState(null);
  const [embeddingStatus, setEmbeddingStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingConfig, setLoadingConfig] = useState(false);
  const [error, setError] = useState(null);
  const [configStatus, setConfigStatus] = useState(null);
  const [judgeConfig, setJudgeConfig] = useState(null);
  const [judgeConfigModified, setJudgeConfigModified] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadOptions();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedAlgorithm && selectedDataset) {
      checkCompatibility();
    } else {
      setCompatibility(null);
      setEmbeddingStatus(null);
    }
  }, [selectedAlgorithm, selectedDataset]);

  const loadOptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const [algosRes, datasetsRes, configRes, judgeRes] = await Promise.all([
        listAlgorithms(),
        listDatasets(),
        getConfigStatus().catch(() => ({ loaded: false })),
        getJudgeConfig().catch(() => null)
      ]);
      
      setAlgorithms(algosRes.algorithms || []);
      setDatasets(datasetsRes.datasets || []);
      setConfigStatus(configRes);
      setJudgeConfig(judgeRes);
      
      // Pre-select if already loaded
      if (configRes.loaded) {
        setSelectedAlgorithm(configRes.algorithm_folder || '');
        setSelectedDataset(configRes.dataset_folder || '');
      }
    } catch (err) {
      setError(`Failed to load options: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const checkCompatibility = async () => {
    try {
      const [compatRes, embedRes] = await Promise.all([
        validateCompatibility(selectedAlgorithm, selectedDataset),
        getEmbeddingStatus(selectedAlgorithm, selectedDataset)
      ]);
      setCompatibility(compatRes);
      setEmbeddingStatus(embedRes);
    } catch (err) {
      setCompatibility({ compatible: false, reason: err.message });
      setEmbeddingStatus(null);
    }
  };

  const handleLoad = async () => {
    if (!compatibility?.compatible) return;
    
    setLoadingConfig(true);
    setError(null);
    
    try {
      // Save judge config if modified
      if (judgeConfigModified && judgeConfig) {
        await updateJudgeConfig(judgeConfig);
        setJudgeConfigModified(false);
      }
      
      const result = await loadConfiguration(selectedAlgorithm, selectedDataset, {
        openaiKey,
        generateEmbeddings: true
      });
      
      setConfigStatus({
        loaded: true,
        algorithm_folder: selectedAlgorithm,
        dataset_folder: selectedDataset,
        ...result
      });
      
      if (onConfigLoaded) {
        onConfigLoaded(result);
      }
    } catch (err) {
      setError(`Failed to load configuration: ${err.message}`);
    } finally {
      setLoadingConfig(false);
    }
  };
  
  const handleJudgeToggle = (provider) => {
    if (!judgeConfig) return;
    
    const newJudges = judgeConfig.judges.map(j => 
      j.provider === provider ? { ...j, enabled: !j.enabled } : j
    );
    
    setJudgeConfig({ ...judgeConfig, judges: newJudges });
    setJudgeConfigModified(true);
  };
  
  const handleNSamplesChange = (value) => {
    if (!judgeConfig) return;
    
    setJudgeConfig({ ...judgeConfig, default_n: parseInt(value) });
    setJudgeConfigModified(true);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white">Settings</h2>
          <p className="text-slate-400 text-sm mt-1">Configure API keys and load algorithm/dataset</p>
        </div>
        
        <div className="p-6 space-y-6">
          {/* API Keys Section */}
          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-3">API Keys</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">OpenAI API Key</label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => onOpenaiKeyChange(e.target.value)}
                  placeholder="sk-..."
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <p className="text-xs text-slate-500 mt-1">Used for embedding generation</p>
              </div>
              
              <div>
                <label className="block text-sm text-slate-400 mb-1">Gemini API Key</label>
                <input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => onGeminiKeyChange(e.target.value)}
                  placeholder="AIza..."
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <p className="text-xs text-slate-500 mt-1">Used for LLM-as-a-judge evaluation</p>
              </div>
              
              <div>
                <label className="block text-sm text-slate-400 mb-1">Anthropic API Key</label>
                <input
                  type="password"
                  value={anthropicKey}
                  onChange={(e) => onAnthropicKeyChange(e.target.value)}
                  placeholder="sk-ant..."
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <p className="text-xs text-slate-500 mt-1">Used for LLM-as-a-judge evaluation</p>
              </div>
            </div>
          </div>
          
          {/* LLM Judge Configuration */}
          {judgeConfig && (
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-3">LLM Judge Configuration</h3>
              
              <div className="space-y-3">
                {/* Provider Toggles */}
                <div className="space-y-2">
                  <label className="block text-xs text-slate-400 mb-2">Enabled Providers</label>
                  {judgeConfig.judges.map(judge => (
                    <label 
                      key={judge.provider}
                      className="flex items-center gap-3 p-2 bg-slate-800 rounded-lg border border-slate-700 hover:border-slate-600 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={judge.enabled}
                        onChange={() => handleJudgeToggle(judge.provider)}
                        className="w-4 h-4 rounded bg-slate-700 border-slate-600 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="flex-1">
                        <div className="text-sm text-white capitalize">{judge.provider}</div>
                        <div className="text-xs text-slate-500">{judge.description || judge.model}</div>
                      </div>
                    </label>
                  ))}
                </div>
                
                {/* N Samples Slider */}
                <div>
                  <label className="block text-xs text-slate-400 mb-2">
                    Samples per Judge (N = {judgeConfig.default_n})
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={judgeConfig.default_n}
                    onChange={(e) => handleNSamplesChange(e.target.value)}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  />
                  <div className="flex justify-between text-xs text-slate-500 mt-1">
                    <span>1 (faster)</span>
                    <span>10 (more reliable)</span>
                  </div>
                </div>
                
                {judgeConfigModified && (
                  <div className="p-2 bg-yellow-500/10 border border-yellow-500/30 rounded text-yellow-400 text-xs">
                    Judge config modified. Changes will be saved when you load configuration.
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Algorithm/Dataset Selection */}
          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-3">Configuration</h3>
            
            {loading ? (
              <p className="text-slate-500">Loading...</p>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Algorithm</label>
                  <select
                    value={selectedAlgorithm}
                    onChange={(e) => setSelectedAlgorithm(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Select algorithm...</option>
                    {algorithms.map(algo => (
                      <option key={algo.folder_name} value={algo.folder_name}>
                        {algo.name} (v{algo.version})
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Dataset</label>
                  <select
                    value={selectedDataset}
                    onChange={(e) => setSelectedDataset(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Select dataset...</option>
                    {datasets.map(ds => (
                      <option key={ds.folder_name} value={ds.folder_name}>
                        {ds.name} ({ds.episode_count} episodes)
                      </option>
                    ))}
                  </select>
                </div>
                
                {/* Compatibility Check */}
                {compatibility && (
                  <div className={`p-3 rounded-lg ${
                    compatibility.compatible 
                      ? 'bg-green-500/10 border border-green-500/30' 
                      : 'bg-red-500/10 border border-red-500/30'
                  }`}>
                    <div className="flex items-center gap-2">
                      <span className={compatibility.compatible ? 'text-green-400' : 'text-red-400'}>
                        {compatibility.compatible ? '✓' : '✗'}
                      </span>
                      <span className={compatibility.compatible ? 'text-green-400' : 'text-red-400'}>
                        {compatibility.compatible ? 'Compatible' : 'Incompatible'}
                      </span>
                    </div>
                    {compatibility.reason && (
                      <p className="text-sm text-slate-400 mt-1">{compatibility.reason}</p>
                    )}
                  </div>
                )}
                
                {/* Embedding Status */}
                {embeddingStatus && (
                  <div className="p-3 bg-slate-800 rounded-lg border border-slate-700">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400 text-sm">Embeddings Cache</span>
                      <span className={embeddingStatus.cached ? 'text-green-400' : 'text-yellow-400'}>
                        {embeddingStatus.cached ? 'Cached' : 'Will Generate'}
                      </span>
                    </div>
                    {embeddingStatus.cached && embeddingStatus.episode_count && (
                      <p className="text-xs text-slate-500 mt-1">
                        {embeddingStatus.episode_count} embeddings available
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Current Status */}
          {configStatus?.loaded && (
            <div className="p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-lg">
              <p className="text-sm text-indigo-400">
                Currently loaded: {configStatus.algorithm_folder} / {configStatus.dataset_folder}
              </p>
            </div>
          )}
          
          {/* Error Display */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>
        
        <div className="p-6 border-t border-slate-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600"
          >
            Cancel
          </button>
          <button
            onClick={handleLoad}
            disabled={!compatibility?.compatible || loadingConfig}
            className={`px-4 py-2 rounded-lg font-medium ${
              !compatibility?.compatible || loadingConfig
                ? 'bg-indigo-600/50 text-indigo-300/50 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-500'
            }`}
          >
            {loadingConfig ? 'Loading...' : 'Load Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
}
