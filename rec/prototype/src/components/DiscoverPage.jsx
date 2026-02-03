/**
 * Discover Page - Two interfaces:
 * 1. Jump In (History) - Shows content user HAS interacted with
 * 2. Recommendations - Shows content user has NOT interacted with
 * 
 * Core principle: Recommendations exclude all viewed/bookmarked/not-interested episodes
 */

import { useState, useEffect, useMemo } from 'react';
import RecommendationSection from './RecommendationSection';
import JumpInSection from './JumpInSection';

const API_BASE = 'http://localhost:8000';

// Credibility floor: episodes with credibility < 2 are not recommended
const CREDIBILITY_FLOOR = 2;

export default function DiscoverPage({ excludedIds, inferred, viewedEpisodes, bookmarkedEpisodes, onView, onBookmark, onNotInterested }) {
  const [allEpisodes, setAllEpisodes] = useState([]);
  const [allSeries, setAllSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Load all data on mount
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [epsRes, seriesRes] = await Promise.all([
          fetch(`${API_BASE}/api/episodes`),
          fetch(`${API_BASE}/api/series`)
        ]);
        
        if (!epsRes.ok || !seriesRes.ok) throw new Error('API error');
        
        const epsData = await epsRes.json();
        const seriesData = await seriesRes.json();
        
        setAllEpisodes(epsData.episodes || []);
        setAllSeries(seriesData.series || []);
      } catch (err) {
        setError('API not running. Start with: cd mock_api && python3 server.py');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);
  
  // AVAILABLE episodes = all episodes MINUS excluded ones
  const availableEpisodes = useMemo(() => {
    return allEpisodes.filter(ep => !excludedIds.has(ep.content_id || ep.id));
  }, [allEpisodes, excludedIds]);
  
  // Quality score calculation with credibility floor
  const qualityScore = (ep) => {
    const s = ep.scores || {};
    // Credibility floor: episodes below threshold get score 0 (filtered out)
    if ((s.credibility || 0) < CREDIBILITY_FLOOR) {
      return 0;
    }
    return (s.insight || 0) * 0.45 + (s.credibility || 0) * 0.40 + (s.information || 0) * 0.15;
  };
  
  // Filter episodes that pass credibility floor
  const credibleEpisodes = useMemo(() => {
    return availableEpisodes.filter(ep => (ep.scores?.credibility || 0) >= CREDIBILITY_FLOOR);
  }, [availableEpisodes]);
  
  // Build recommendation sections
  const sections = useMemo(() => {
    const result = [];
    const isColdStart = inferred.totalViewed < 2;
    const categoryPrefs = Object.fromEntries(inferred.topCategories);
    const topCategory = inferred.topCategories[0]?.[0];
    const subscribedIds = new Set(inferred.implicitSubscriptions.map(s => s.id));
    
    // Series popularity map
    const seriesPop = {};
    allSeries.forEach(s => seriesPop[s.id] = s.serafis_score || s.popularity || 50);
    
    // === COLD START: Show global quality ===
    if (isColdStart) {
      const topQuality = [...credibleEpisodes]
        .sort((a, b) => qualityScore(b) - qualityScore(a))
        .slice(0, 12);
      
      result.push({
        section: 'highest_signal',
        title: '💎 Highest Signal',
        subtitle: 'Top quality episodes you haven\'t seen',
        why: `Cold start: Showing globally top-rated content (credibility ≥${CREDIBILITY_FLOOR}, then 45% insight + 40% credibility + 15% info)`,
        episodes: topQuality,
      });
    } else {
      // === PERSONALIZED: Insights for You ===
      const forYou = credibleEpisodes
        .filter(ep => (ep.categories?.major || []).some(c => categoryPrefs[c] > 0))
        .sort((a, b) => {
          const aMatch = (a.categories?.major || []).reduce((sum, c) => sum + (categoryPrefs[c] || 0), 0);
          const bMatch = (b.categories?.major || []).reduce((sum, c) => sum + (categoryPrefs[c] || 0), 0);
          return (bMatch + qualityScore(b)) - (aMatch + qualityScore(a));
        })
        .slice(0, 10);
      
      if (forYou.length > 0) {
        result.push({
          section: 'insights_for_you',
          title: '📊 Insights for You',
          subtitle: `Based on ${inferred.topCategories.slice(0, 2).map(([c]) => c).join(', ')}`,
          why: `Credibility ≥${CREDIBILITY_FLOOR} required. Matching interests: ${inferred.topCategories.map(([c, s]) => `${c} (+${s})`).join(', ')}`,
          episodes: forYou,
        });
      }
      
      // === Highest Signal (excluding what you've seen) ===
      const highSignal = [...credibleEpisodes]
        .sort((a, b) => qualityScore(b) - qualityScore(a))
        .slice(0, 10);
      
      result.push({
        section: 'highest_signal',
        title: '💎 Highest Signal This Week',
        subtitle: 'Top quality you haven\'t seen yet',
        why: `Credibility ≥${CREDIBILITY_FLOOR} required. Pure quality ranking of unseen episodes`,
        episodes: highSignal,
      });
    }
    
    // === Non-Consensus Ideas (already filters for credibility >= 3) ===
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
        title: '🔥 Non-Consensus Ideas',
        subtitle: 'Contrarian views from credible speakers',
        why: 'Requires credibility ≥3. Has critical_views data OR (insight ≥3 + credibility ≥3 + entertainment ≤2)',
        episodes: contrarian,
      });
    }
    
    // === New from Your Shows (if subscriptions) - uses credible episodes ===
    if (subscribedIds.size > 0) {
      const fromSubs = credibleEpisodes
        .filter(ep => subscribedIds.has(ep.series?.id))
        .sort((a, b) => new Date(b.published_at || 0) - new Date(a.published_at || 0))
        .slice(0, 8);
      
      if (fromSubs.length > 0) {
        result.push({
          section: 'new_from_shows',
          title: '📡 New from Your Shows',
          subtitle: inferred.implicitSubscriptions.map(s => s.name).slice(0, 2).join(', '),
          why: `Credibility ≥${CREDIBILITY_FLOOR} required. You viewed 2+ episodes from these series = implicit subscription`,
          episodes: fromSubs,
        });
      }
    }
    
    // === Trending in Category ===
    if (topCategory && !isColdStart) {
      const trending = credibleEpisodes
        .filter(ep => (ep.categories?.major || []).includes(topCategory))
        .sort((a, b) => {
          const aPop = seriesPop[a.series?.id] || 50;
          const bPop = seriesPop[b.series?.id] || 50;
          return (bPop * 0.5 + qualityScore(b) * 0.3) - (aPop * 0.5 + qualityScore(a) * 0.3);
        })
        .slice(0, 8);
      
      if (trending.length > 0) {
        result.push({
          section: 'trending',
          title: `🌟 Trending in ${topCategory}`,
          subtitle: 'Popular from top-rated series',
          why: `Credibility ≥${CREDIBILITY_FLOOR} required. 50% series popularity + 30% quality + 20% recency`,
          episodes: trending,
        });
      }
    }
    
    return result;
  }, [credibleEpisodes, allSeries, inferred]);
  
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
          <code className="bg-slate-800 px-3 py-2 rounded text-green-400 text-sm">
            cd mock_api && python3 server.py
          </code>
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
            <span className="text-slate-500">Credible (≥{CREDIBILITY_FLOOR}):</span>{' '}
            <span className="text-yellow-400">{credibleEpisodes.length}</span>
          </div>
          <div>
            <span className="text-slate-500">Viewed:</span>{' '}
            <span className="text-blue-400">{viewedEpisodes?.length || 0}</span>
          </div>
          <div>
            <span className="text-slate-500">Excluded:</span>{' '}
            <span className="text-red-400">{excludedIds.size}</span>
          </div>
        </div>
      </div>
      
      {/* Jump In Section - History interface (shows viewed content) */}
      <JumpInSection 
        viewedEpisodes={viewedEpisodes || []} 
        bookmarkedEpisodes={bookmarkedEpisodes || []} 
      />
      
      {/* Separator between history and recommendations */}
      {(viewedEpisodes?.length > 0 || bookmarkedEpisodes?.length > 0) && (
        <div className="mx-4 mb-4 flex items-center gap-3">
          <div className="flex-1 h-px bg-slate-700" />
          <span className="text-xs text-slate-500 uppercase tracking-wider">Recommendations</span>
          <div className="flex-1 h-px bg-slate-700" />
        </div>
      )}
      
      {/* Cold start hint */}
      {inferred.totalViewed < 2 && (
        <div className="mx-4 mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-300">
            <strong>Cold Start:</strong> View 2+ episodes to unlock personalized recommendations.
          </p>
        </div>
      )}
      
      {/* Recommendation sections */}
      {sections.map((section) => (
        <RecommendationSection
          key={section.section}
          section={section}
          onView={onView}
          onBookmark={onBookmark}
          onNotInterested={onNotInterested}
        />
      ))}
      
      {credibleEpisodes.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          You've seen everything! Click Reset to start over.
        </div>
      )}
    </div>
  );
}
