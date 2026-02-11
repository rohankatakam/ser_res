/**
 * For You Page - Personalized Recommendations
 * 
 * Session-based feed with:
 * - Load More: Get next 10 from queue
 * - Refresh: Create new session with fresh rankings
 * 
 * FIXED: Properly handles engagement updates from other tabs
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { createSession, loadMore as loadMoreApi, fetchStats, getConfigStatus, getEmbeddingStatus } from '../api';

export default function ForYouPage({ 
  engagements,
  excludedIds,
  activeSessionId,
  onSessionChange,
  onView, 
  onBookmark, 
  onNotInterested,
  configRefreshKey = 0
}) {
  const [sessionId, setSessionId] = useState(activeSessionId);
  const [episodes, setEpisodes] = useState([]);
  const [queueInfo, setQueueInfo] = useState({ total: 0, shown: 0, remaining: 0 });
  const [coldStart, setColdStart] = useState(true);
  const [debugInfo, setDebugInfo] = useState(null);
  const [apiStats, setApiStats] = useState(null);
  const [embeddingStatus, setEmbeddingStatus] = useState(null);
  const [checkingEmbeddings, setCheckingEmbeddings] = useState(false);
  
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  
  // Track engagement count to detect changes
  const lastEngagementCount = useRef(0);
  const [engagementsDirty, setEngagementsDirty] = useState(false);
  
  // Track config refresh key to detect parameter changes
  const lastConfigRefreshKey = useRef(configRefreshKey);
  
  // Detect when engagements change from outside this component
  useEffect(() => {
    const currentCount = engagements?.length || 0;
    if (currentCount !== lastEngagementCount.current) {
      lastEngagementCount.current = currentCount;
      if (!loading) {
        setEngagementsDirty(true);
      }
    }
  }, [engagements, loading]);
  
  // Detect when config refresh key changes (parameter tuning applied)
  useEffect(() => {
    if (configRefreshKey !== lastConfigRefreshKey.current) {
      lastConfigRefreshKey.current = configRefreshKey;
      console.log('[ForYouPage] Config refresh triggered, fetching new session');
      fetchSession(true);
    }
  }, [configRefreshKey]);
  
  // Check embedding status periodically if embeddings are missing
  useEffect(() => {
    const checkEmbeddings = async () => {
      if (apiStats?.total_embeddings === 0 && !checkingEmbeddings) {
        setCheckingEmbeddings(true);
        try {
          const config = await getConfigStatus();
          if (config.loaded && config.algorithm_folder && config.dataset_folder) {
            const status = await getEmbeddingStatus(config.algorithm_folder, config.dataset_folder);
            setEmbeddingStatus(status);
            
            // If embeddings are now available, refresh the page
            if (status.cached && status.count > 0 && apiStats?.total_embeddings === 0) {
              console.log('[ForYouPage] Embeddings now available, refreshing session');
              fetchSession(true);
            }
          }
        } catch (err) {
          console.warn('Failed to check embedding status:', err);
        } finally {
          setCheckingEmbeddings(false);
        }
      }
    };
    
    // Check immediately
    checkEmbeddings();
    
    // Set up polling every 3 seconds if embeddings are missing
    if (apiStats?.total_embeddings === 0) {
      const interval = setInterval(checkEmbeddings, 3000);
      return () => clearInterval(interval);
    }
  }, [apiStats?.total_embeddings, checkingEmbeddings]);
  
  // Core fetch function - creates a new session
  const fetchSession = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setRefreshing(!showLoading);
    
    try {
      // Convert excludedIds Set to Array for API
      const excludedArray = excludedIds ? Array.from(excludedIds) : [];
      const engagementsArray = engagements || [];
      
      console.log('[ForYouPage] Creating session with:', {
        engagements: engagementsArray.length,
        excluded: excludedArray.length
      });
      
      const [sessionResult, stats] = await Promise.all([
        createSession(engagementsArray, excludedArray),
        fetchStats().catch(() => null)
      ]);
      
      console.log('[ForYouPage] Session created:', {
        sessionId: sessionResult.session_id,
        userVectorEpisodes: sessionResult.debug?.user_vector_episodes,
        coldStart: sessionResult.cold_start
      });
      
      setSessionId(sessionResult.session_id);
      setEpisodes(sessionResult.episodes || []);
      setQueueInfo({
        total: sessionResult.total_in_queue,
        shown: sessionResult.shown_count,
        remaining: sessionResult.remaining_count
      });
      setColdStart(sessionResult.cold_start);
      setDebugInfo(sessionResult.debug);
      setApiStats(stats);
      setEngagementsDirty(false);
      onSessionChange?.(sessionResult.session_id);
      
    } catch (err) {
      console.error('[ForYouPage] Failed to create session:', err);
      // Check if it's a config issue vs API down
      const errorMsg = err.message || '';
      if (errorMsg.includes('config/load') || errorMsg.includes('No algorithm')) {
        setError('No configuration loaded. Click Settings to load an algorithm and dataset.');
      } else if (errorMsg.includes('Failed to fetch')) {
        setError('API not running. Start the backend server.');
      } else {
        setError(errorMsg || 'Failed to create session. Check the backend server.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [engagements, excludedIds, onSessionChange]);
  
  // Initialize on mount - check if config is loaded first
  useEffect(() => {
    const initSession = async () => {
      try {
        // Check if configuration is loaded before trying to create session
        const configStatus = await getConfigStatus();
        if (configStatus.loaded) {
          fetchSession(true);
        } else {
          setError('No configuration loaded. Click Settings to load an algorithm and dataset.');
          setLoading(false);
        }
      } catch (err) {
        console.error('[ForYouPage] Failed to check config status:', err);
        setError('Failed to connect to backend. Is the server running?');
        setLoading(false);
      }
    };
    
    initSession();
  }, []); // Only on mount
  
  // Handle Refresh button click
  const handleRefresh = useCallback(() => {
    fetchSession(false);
  }, [fetchSession]);
  
  // Handle Load More
  const handleLoadMore = useCallback(async () => {
    if (!sessionId || loadingMore || queueInfo.remaining <= 0) return;
    
    setLoadingMore(true);
    try {
      const result = await loadMoreApi(sessionId, 10);
      setEpisodes(prev => [...prev, ...(result.episodes || [])]);
      setQueueInfo({
        total: result.total_in_queue,
        shown: result.shown_count,
        remaining: result.remaining_count
      });
    } catch (err) {
      console.error('Failed to load more:', err);
    } finally {
      setLoadingMore(false);
    }
  }, [sessionId, loadingMore, queueInfo.remaining]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-pulse text-slate-400">Loading recommendations...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-96 p-4">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <code className="bg-slate-800 px-3 py-2 rounded text-green-400 text-sm">
            cd rec/mock_api && python server.py
          </code>
        </div>
      </div>
    );
  }
  
  return (
    <div className="p-4 pb-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">
            {coldStart ? 'Highest Signal' : 'For You'}
          </h1>
          <p className="text-slate-400 text-sm">
            {coldStart 
              ? 'Top quality episodes • Click to build your profile'
              : `Personalized from ${engagements?.length || 0} engagements`
            }
          </p>
        </div>
        <div className="flex items-center gap-2">
          {engagementsDirty && (
            <span className="text-xs text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded">
              New activity detected
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 ${
              engagementsDirty 
                ? 'bg-yellow-500 text-black hover:bg-yellow-400' 
                : 'bg-indigo-600 text-white hover:bg-indigo-500'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {refreshing ? (
              <>
                <span className="animate-spin">↻</span>
                Refreshing...
              </>
            ) : (
              <>↻ Refresh Feed</>
            )}
          </button>
        </div>
      </div>
      
      {/* Cold Start Hint */}
      {coldStart && (engagements?.length || 0) < 2 && (
        <div className="mb-6 p-4 bg-indigo-500/10 border border-indigo-500/30 rounded-xl">
          <p className="text-sm text-indigo-300">
            <strong>Getting started:</strong> Click on episodes that interest you. 
            After 2+ interactions, we'll personalize your feed using semantic matching.
          </p>
          {apiStats?.total_embeddings === 0 && (
            <div className="mt-2">
              {embeddingStatus?.cached === false && !embeddingStatus?.error ? (
                <p className="text-sm text-blue-300 flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Generating embeddings... This may take 30-60 seconds.
                </p>
              ) : (
                <p className="text-sm text-yellow-300">
                  Note: No embeddings found. Go to Settings to load a configuration with embeddings.
                </p>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Debug Info Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-slate-800/50 rounded-lg text-xs">
        <span className="text-slate-400">
          Queue: <span className="text-white">{episodes.length}/{queueInfo.total}</span>
        </span>
        <span className="text-slate-400">
          Remaining: <span className="text-green-400">{queueInfo.remaining}</span>
        </span>
        <span className="text-slate-400">
          Vector: <span className="text-purple-400">{debugInfo?.user_vector_episodes || 0} eps</span>
        </span>
        {debugInfo?.top_similarity_scores?.[0] && (
          <span className="text-slate-400">
            Top sim: <span className="text-indigo-400">{(debugInfo.top_similarity_scores[0] * 100).toFixed(0)}%</span>
          </span>
        )}
        {sessionId && (
          <span className="text-slate-500 font-mono ml-auto">
            {sessionId}
          </span>
        )}
      </div>
      
      {/* Episodes List */}
      <div className="space-y-4">
        {episodes.map((episode, index) => (
          <RecommendationCard
            key={`${episode.id}-${index}`}
            episode={episode}
            onView={onView}
            onBookmark={onBookmark}
            onNotInterested={onNotInterested}
          />
        ))}
      </div>
      
      {/* Load More */}
      {queueInfo.remaining > 0 && (
        <div className="mt-8 text-center">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="px-8 py-3 bg-slate-800 text-white rounded-xl hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed border border-slate-700"
          >
            {loadingMore ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin">↻</span>
                Loading...
              </span>
            ) : (
              `Load More (${queueInfo.remaining} remaining)`
            )}
          </button>
        </div>
      )}
      
      {queueInfo.remaining === 0 && episodes.length > 0 && (
        <div className="mt-8 text-center text-slate-500">
          You've seen all recommendations • 
          <button onClick={handleRefresh} className="text-indigo-400 ml-1 hover:underline">
            Refresh for new rankings
          </button>
        </div>
      )}
    </div>
  );
}

function RecommendationCard({ episode, onView, onBookmark, onNotInterested }) {
  const { title, series, published_at, scores, key_insight, similarity_score, queue_position, categories, badges } = episode;
  
  const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
  
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden hover:border-indigo-500/50 transition-colors">
      <div 
        onClick={() => onView?.(episode)}
        className="p-4 cursor-pointer"
      >
        {/* Top Row: Position & Match */}
        <div className="flex items-center gap-2 mb-3">
          {queue_position && (
            <span className="text-xs font-mono px-2 py-1 bg-slate-700 rounded text-slate-400">
              #{queue_position}
            </span>
          )}
          {similarity_score !== null && similarity_score !== undefined && (
            <span className="text-xs px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded font-medium">
              {(similarity_score * 100).toFixed(0)}% match
            </span>
          )}
          {badges?.includes('high_insight') && (
            <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-400 rounded">
              High Insight
            </span>
          )}
          <span className="text-xs text-slate-500 ml-auto">{formatDate(published_at)}</span>
        </div>
        
        {/* Main Content */}
        <div className="flex gap-4">
          <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold flex-shrink-0 text-lg">
            {series?.name?.charAt(0) || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-white mb-1 line-clamp-2">
              {title}
            </h3>
            <p className="text-sm text-slate-400 mb-2">{series?.name}</p>
            
            {/* Scores */}
            <div className="flex items-center gap-3 text-xs">
              <span className="text-yellow-400">Credibility: {scores?.credibility || 0}</span>
              <span className="text-purple-400">Insight: {scores?.insight || 0}</span>
              <span className="text-blue-400">Info: {scores?.information || 0}</span>
            </div>
          </div>
        </div>
        
        {/* Key Insight */}
        {key_insight && (
          <p className="mt-3 text-sm text-slate-400 line-clamp-2 italic">
            "{key_insight}"
          </p>
        )}
        
        {/* Categories */}
        {categories?.major?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {categories.major.slice(0, 3).map(cat => (
              <span key={cat} className="text-xs px-2 py-0.5 bg-slate-700 rounded text-slate-400">
                {cat}
              </span>
            ))}
          </div>
        )}
      </div>
      
      {/* Actions */}
      <div className="flex border-t border-slate-700">
        <button
          onClick={(e) => { e.stopPropagation(); onView?.(episode); }}
          className="flex-1 py-3 text-sm text-indigo-400 hover:bg-indigo-500/10 font-medium"
        >
          View Details
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onBookmark?.(episode); }}
          className="flex-1 py-3 text-sm text-purple-400 hover:bg-purple-500/10 border-l border-slate-700 font-medium"
        >
          Save
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onNotInterested?.(episode); }}
          className="px-4 py-3 text-sm text-slate-500 hover:bg-slate-700 border-l border-slate-700"
          title="Not interested"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
