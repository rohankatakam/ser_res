/**
 * Discover Page - V1.1 Session Pool (Option C)
 * 
 * Feed Behavior:
 * - On mount: Creates session, gets first 10 recommendations
 * - Load More: Gets next 10 from session queue (no recomputation)
 * - Refresh: Creates new session with fresh computation
 * 
 * The queue is deterministic within a session - "Load More" always
 * returns the next items in the pre-computed ranking order.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import RecommendationSection from './RecommendationSection';
import JumpInSection from './JumpInSection';
import { createSession, loadMore as loadMoreApi, fetchStats } from '../api';

const API_BASE = 'http://localhost:8000';

// V1.1 Configuration
const CREDIBILITY_FLOOR = 2;
const PAGE_SIZE = 10;

export default function DiscoverPage({ 
  excludedIds, 
  inferred, 
  viewedEpisodes, 
  bookmarkedEpisodes,
  engagements,
  activeSessionId,
  onSessionChange,
  onView, 
  onBookmark, 
  onNotInterested 
}) {
  const [allEpisodes, setAllEpisodes] = useState([]);
  const [allSeries, setAllSeries] = useState([]);
  
  // Session-based state
  const [sessionId, setSessionId] = useState(activeSessionId);
  const [forYouEpisodes, setForYouEpisodes] = useState([]);
  const [queueInfo, setQueueInfo] = useState({ total: 0, shown: 0, remaining: 0 });
  const [coldStart, setColdStart] = useState(true);
  const [debugInfo, setDebugInfo] = useState(null);
  
  const [apiStats, setApiStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [showAllEpisodes, setShowAllEpisodes] = useState(false);
  
  // Load base data on mount
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [epsRes, seriesRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/episodes`),
          fetch(`${API_BASE}/api/series`),
          fetchStats().catch(() => null)
        ]);
        
        if (!epsRes.ok || !seriesRes.ok) throw new Error('API error');
        
        const epsData = await epsRes.json();
        const seriesData = await seriesRes.json();
        
        setAllEpisodes(epsData.episodes || []);
        setAllSeries(seriesData.series || []);
        setApiStats(statsRes);
      } catch (err) {
        setError('API not running. Start with: cd mock_api && python server.py');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);
  
  // Create initial session when episodes are loaded
  useEffect(() => {
    if (!allEpisodes.length || sessionId) return;
    
    async function initSession() {
      try {
        const result = await createSession(engagements || [], Array.from(excludedIds || []));
        
        setSessionId(result.session_id);
        setForYouEpisodes(result.episodes || []);
        setQueueInfo({
          total: result.total_in_queue,
          shown: result.shown_count,
          remaining: result.remaining_count
        });
        setColdStart(result.cold_start);
        setDebugInfo(result.debug);
        
        // Notify parent of session change
        onSessionChange?.(result.session_id);
      } catch (err) {
        console.error('Failed to create session:', err);
      }
    }
    
    initSession();
  }, [allEpisodes.length, sessionId, engagements, excludedIds, onSessionChange]);
  
  // Handle Load More
  const handleLoadMore = useCallback(async () => {
    if (!sessionId || loadingMore || queueInfo.remaining <= 0) return;
    
    setLoadingMore(true);
    try {
      const result = await loadMoreApi(sessionId, PAGE_SIZE);
      
      // Append new episodes to existing list
      setForYouEpisodes(prev => [...prev, ...(result.episodes || [])]);
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
  
  // Handle Refresh (create new session)
  const handleRefresh = useCallback(async () => {
    if (refreshing) return;
    
    setRefreshing(true);
    try {
      // Create fresh session with current engagements
      const result = await createSession(engagements || [], Array.from(excludedIds || []));
      
      setSessionId(result.session_id);
      setForYouEpisodes(result.episodes || []);
      setQueueInfo({
        total: result.total_in_queue,
        shown: result.shown_count,
        remaining: result.remaining_count
      });
      setColdStart(result.cold_start);
      setDebugInfo(result.debug);
      
      // Notify parent of session change
      onSessionChange?.(result.session_id);
    } catch (err) {
      console.error('Failed to refresh session:', err);
    } finally {
      setRefreshing(false);
    }
  }, [refreshing, engagements, excludedIds, onSessionChange]);
  
  // AVAILABLE episodes = all episodes MINUS excluded ones
  const availableEpisodes = useMemo(() => {
    return allEpisodes.filter(ep => !excludedIds.has(ep.content_id) && !excludedIds.has(ep.id));
  }, [allEpisodes, excludedIds]);
  
  // Credible episodes (pass quality gates)
  const credibleEpisodes = useMemo(() => {
    return availableEpisodes.filter(ep => {
      const scores = ep.scores || {};
      return scores.credibility >= CREDIBILITY_FLOOR && 
             (scores.credibility + scores.insight) >= 5;
    });
  }, [availableEpisodes]);
  
  // Quality score for fallback sorting
  const qualityScore = (ep) => {
    const s = ep.scores || {};
    if ((s.credibility || 0) < CREDIBILITY_FLOOR) return 0;
    return (s.insight || 0) * 0.45 + (s.credibility || 0) * 0.40 + (s.information || 0) * 0.15;
  };
  
  // Build additional sections (Non-Consensus, etc.)
  const additionalSections = useMemo(() => {
    const result = [];
    
    // Only show additional sections if For You is sparse
    if (forYouEpisodes.length >= 5) return result;
    
    // Non-Consensus Ideas
    const contrarian = credibleEpisodes
      .filter(ep => {
        if (ep.critical_views?.has_critical_views) return true;
        const s = ep.scores || {};
        return s.insight >= 3 && s.credibility >= 3 && (s.entertainment || 3) <= 2;
      })
      .sort((a, b) => {
        const aReal = a.critical_views?.has_critical_views ? 10 : 0;
        const bReal = b.critical_views?.has_critical_views ? 10 : 0;
        return (bReal + qualityScore(b)) - (aReal + qualityScore(a));
      })
      .slice(0, 8);
    
    if (contrarian.length > 0) {
      result.push({
        section: 'non_consensus',
        title: 'Non-Consensus Ideas',
        subtitle: 'Contrarian views from credible speakers',
        episodes: contrarian,
      });
    }
    
    return result;
  }, [credibleEpisodes, forYouEpisodes.length]);
  
  // Episodes for browsing grid
  const browsingEpisodes = useMemo(() => {
    return [...availableEpisodes]
      .sort((a, b) => new Date(b.published_at) - new Date(a.published_at))
      .slice(0, showAllEpisodes ? 100 : 24);
  }, [availableEpisodes, showAllEpisodes]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-pulse text-slate-400">Loading...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-96 p-4">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <code className="bg-slate-800 px-3 py-2 rounded text-green-400 text-sm block mb-4">
            cd rec/mock_api && python server.py
          </code>
          <p className="text-slate-500 text-sm">
            Make sure to run the API server first.
          </p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="pb-8">
      {/* Stats bar */}
      <div className="px-4 py-3 bg-slate-800/50 border-b border-slate-700 mb-4">
        <div className="flex flex-wrap gap-4 text-sm">
          <div>
            <span className="text-slate-500">Total:</span>{' '}
            <span className="text-white">{allEpisodes.length}</span>
          </div>
          <div>
            <span className="text-slate-500">Queue:</span>{' '}
            <span className="text-yellow-400">{queueInfo.shown}/{queueInfo.total}</span>
          </div>
          <div>
            <span className="text-slate-500">Remaining:</span>{' '}
            <span className="text-green-400">{queueInfo.remaining}</span>
          </div>
          <div>
            <span className="text-slate-500">Engagements:</span>{' '}
            <span className="text-blue-400">{engagements?.length || 0}</span>
          </div>
          {sessionId && (
            <div>
              <span className="text-slate-500">Session:</span>{' '}
              <span className="text-purple-400 font-mono text-xs">{sessionId}</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Jump In Section - History (shows engaged content) */}
      <JumpInSection 
        viewedEpisodes={viewedEpisodes || []} 
        bookmarkedEpisodes={bookmarkedEpisodes || []} 
      />
      
      {/* Separator */}
      {(viewedEpisodes?.length > 0 || bookmarkedEpisodes?.length > 0) && (
        <div className="mx-4 mb-4 flex items-center gap-3">
          <div className="flex-1 h-px bg-slate-700" />
          <span className="text-xs text-slate-500 uppercase tracking-wider">Recommendations</span>
          <div className="flex-1 h-px bg-slate-700" />
        </div>
      )}
      
      {/* Cold start hint */}
      {coldStart && (engagements?.length || 0) < 2 && (
        <div className="mx-4 mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-300">
            <strong>Cold Start Mode:</strong> Click on 2+ episodes to unlock personalized "For You" recommendations.
            {apiStats?.total_embeddings === 0 && (
              <span className="block mt-1 text-yellow-300">
                No embeddings found. Run: <code className="bg-slate-800 px-1 rounded">python generate_embeddings.py</code>
              </span>
            )}
          </p>
        </div>
      )}
      
      {/* For You Section (V1.1 Session Pool) */}
      {forYouEpisodes.length > 0 && (
        <div className="mb-6">
          <div className="px-4 mb-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  {coldStart ? '💎 Highest Signal' : '✨ For You'}
                </h2>
                <p className="text-sm text-slate-400">
                  {coldStart ? 'Top quality episodes' : 'Based on your activity'}
                  {' '} • Showing {forYouEpisodes.length} of {queueInfo.total}
                </p>
              </div>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {refreshing ? (
                  <>
                    <span className="animate-spin">⟳</span>
                    Refreshing...
                  </>
                ) : (
                  <>
                    ⟳ Refresh Feed
                  </>
                )}
              </button>
            </div>
            
            {/* Debug info */}
            {debugInfo && (
              <div className="mt-2 p-2 bg-slate-800/50 rounded text-xs text-slate-400 font-mono">
                <span>Candidates: {debugInfo.candidates_count}</span>
                {debugInfo.user_vector_episodes > 0 && (
                  <span className="ml-3">User Vector: {debugInfo.user_vector_episodes} eps</span>
                )}
                {debugInfo.top_similarity_scores && debugInfo.top_similarity_scores.length > 0 && (
                  <span className="ml-3">
                    Top Sims: [{debugInfo.top_similarity_scores.join(', ')}]
                  </span>
                )}
              </div>
            )}
          </div>
          
          <div className="px-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {forYouEpisodes.map((ep, index) => (
                <EpisodeCardWithScore
                  key={`${ep.id}-${index}`}
                  episode={ep}
                  onView={onView}
                  onBookmark={onBookmark}
                  onNotInterested={onNotInterested}
                />
              ))}
            </div>
            
            {/* Load More Button */}
            {queueInfo.remaining > 0 && (
              <div className="mt-6 text-center">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="px-6 py-3 bg-slate-700 text-white rounded-lg hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingMore ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin">⟳</span>
                      Loading...
                    </span>
                  ) : (
                    <span>
                      Load More ({queueInfo.remaining} remaining)
                    </span>
                  )}
                </button>
                <p className="text-xs text-slate-500 mt-2">
                  Queue is deterministic • Same ranking order preserved
                </p>
              </div>
            )}
            
            {queueInfo.remaining === 0 && forYouEpisodes.length > 0 && (
              <div className="mt-6 text-center text-slate-500 text-sm">
                You've seen all recommendations • 
                <button onClick={handleRefresh} className="text-indigo-400 ml-1 hover:underline">
                  Refresh for new rankings
                </button>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Additional sections */}
      {additionalSections.map((section) => (
        <RecommendationSection
          key={section.section}
          section={section}
          onView={onView}
          onBookmark={onBookmark}
          onNotInterested={onNotInterested}
        />
      ))}
      
      {/* Episode Browsing Grid */}
      <div className="px-4 mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white">Browse Episodes</h2>
          <button
            onClick={() => setShowAllEpisodes(!showAllEpisodes)}
            className="text-sm text-indigo-400 hover:text-indigo-300"
          >
            {showAllEpisodes ? 'Show Less' : `Show All (${availableEpisodes.length})`}
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {browsingEpisodes.map((ep) => (
            <BrowseEpisodeCard
              key={ep.id}
              episode={ep}
              onView={onView}
              onBookmark={onBookmark}
            />
          ))}
        </div>
      </div>
      
      {credibleEpisodes.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          You've seen everything! Click Reset to start over.
        </div>
      )}
    </div>
  );
}

// Episode card with similarity score and queue position
function EpisodeCardWithScore({ episode, onView, onBookmark, onNotInterested }) {
  const { title, series, published_at, scores, key_insight, critical_views, similarity_score, queue_position } = episode;
  
  const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
  
  const badges = [];
  if (critical_views?.has_critical_views || critical_views?.non_consensus_level) {
    badges.push('contrarian');
  }
  if (scores?.insight >= 3) badges.push('high_insight');
  
  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden hover:border-indigo-500/50 transition-colors">
      <div 
        onClick={() => onView?.(episode)}
        className="p-4 cursor-pointer hover:bg-slate-750"
      >
        {/* Score bar */}
        <div className="mb-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            {queue_position && (
              <span className="text-xs px-2 py-0.5 bg-slate-700 text-slate-400 rounded">
                #{queue_position}
              </span>
            )}
            {similarity_score !== null && similarity_score !== undefined && (
              <span className="text-xs px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded font-mono">
                {(similarity_score * 100).toFixed(1)}% match
              </span>
            )}
          </div>
          <span className="text-xs text-slate-500">
            C:{scores?.credibility || 0} I:{scores?.insight || 0}
          </span>
        </div>
        
        {/* Header */}
        <div className="flex gap-3 mb-3">
          <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold flex-shrink-0">
            {series?.name?.charAt(0) || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-white line-clamp-2 leading-tight">
              {title}
            </h3>
            <p className="text-xs text-slate-400 truncate">{series?.name}</p>
          </div>
        </div>
        
        {/* Badges and date */}
        <div className="flex items-center gap-2 mb-2 text-xs">
          {badges.includes('contrarian') && (
            <span className="px-1.5 py-0.5 bg-orange-500/20 text-orange-400 rounded">Contrarian</span>
          )}
          {badges.includes('high_insight') && (
            <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded">High Insight</span>
          )}
          <span className="text-slate-500 ml-auto">{formatDate(published_at)}</span>
        </div>
        
        {/* Key insight preview */}
        {key_insight && (
          <p className="text-xs text-slate-400 line-clamp-2">"{key_insight}"</p>
        )}
      </div>
      
      {/* Actions */}
      <div className="flex border-t border-slate-700">
        <button
          onClick={(e) => { e.stopPropagation(); onView?.(episode); }}
          className="flex-1 py-2 text-xs text-indigo-400 hover:bg-indigo-500/20"
        >
          View Details
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onBookmark?.(episode); }}
          className="flex-1 py-2 text-xs text-purple-400 hover:bg-purple-500/20 border-l border-slate-700"
        >
          Save
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onNotInterested?.(episode); }}
          className="py-2 px-3 text-xs text-slate-500 hover:bg-slate-700 border-l border-slate-700"
          title="Not interested"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

// Browse grid card (compact)
function BrowseEpisodeCard({ episode, onView, onBookmark }) {
  const { title, series, scores, published_at, critical_views } = episode;
  
  const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
  
  const isContrarian = critical_views?.has_critical_views || critical_views?.non_consensus_level;
  
  return (
    <div 
      onClick={() => onView?.(episode)}
      className="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:border-indigo-500/50 cursor-pointer transition-colors"
    >
      <div className="flex gap-3">
        <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold flex-shrink-0">
          {series?.name?.charAt(0) || '?'}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white line-clamp-2 leading-tight mb-1">
            {title}
          </h3>
          <p className="text-xs text-slate-400 truncate">{series?.name}</p>
          <div className="flex items-center gap-2 mt-2 text-xs">
            <span className="text-yellow-400">C:{scores?.credibility}</span>
            <span className="text-purple-400">I:{scores?.insight}</span>
            {isContrarian && <span className="text-orange-400">Contrarian</span>}
            <span className="text-slate-500 ml-auto">{formatDate(published_at)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
