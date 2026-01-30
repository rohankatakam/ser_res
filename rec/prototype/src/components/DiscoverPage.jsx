/**
 * Discover Page - Session-based recommendations with transparent "why"
 */

import { useState, useEffect, useMemo } from 'react';
import { fetchApiInfo } from '../api';
import RecommendationSection from './RecommendationSection';

const API_BASE = 'http://localhost:8000';

export default function DiscoverPage({ session, inferred, onEpisodeClick, onNotInterested, onSave }) {
  const [allEpisodes, setAllEpisodes] = useState([]);
  const [allSeries, setAllSeries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Load all data on mount
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch episodes and series directly
        const [epsRes, seriesRes] = await Promise.all([
          fetch(`${API_BASE}/api/episodes`),
          fetch(`${API_BASE}/api/series`)
        ]);
        
        if (!epsRes.ok || !seriesRes.ok) {
          throw new Error('Failed to fetch data');
        }
        
        const epsData = await epsRes.json();
        const seriesData = await seriesRes.json();
        
        setAllEpisodes(epsData.episodes || []);
        setAllSeries(seriesData.series || []);
      } catch (err) {
        console.error('Failed to load data:', err);
        setError('Failed to load data. Make sure the API server is running on port 8000.');
      } finally {
        setLoading(false);
      }
    }
    
    loadData();
  }, []);
  
  // Get excluded episode IDs
  const excludedIds = useMemo(() => {
    const ids = new Set();
    session.notInterested.forEach(ep => ids.add(ep.content_id || ep.id));
    return ids;
  }, [session.notInterested]);
  
  // Filter out excluded episodes
  const availableEpisodes = useMemo(() => {
    return allEpisodes.filter(ep => !excludedIds.has(ep.content_id || ep.id));
  }, [allEpisodes, excludedIds]);
  
  // Calculate quality score
  const qualityScore = (ep) => {
    const scores = ep.scores || {};
    return (scores.insight || 0) * 0.45 + (scores.credibility || 0) * 0.40 + (scores.information || 0) * 0.15;
  };
  
  // Generate sections based on session state
  const sections = useMemo(() => {
    const result = [];
    const isColdStart = session.clicks.length < 2;
    
    // Get category preferences
    const categoryPrefs = {};
    inferred.topCategories.forEach(([cat, score]) => {
      categoryPrefs[cat] = score;
    });
    const topCategory = inferred.topCategories[0]?.[0];
    
    // Get implicit subscriptions
    const subscribedSeriesIds = new Set(
      inferred.implicitSubscriptions.map(s => s.id)
    );
    
    // === SECTION 1: Insights for You (or Cold Start) ===
    if (isColdStart) {
      // Cold start: Show highest signal globally
      const highSignal = [...availableEpisodes]
        .sort((a, b) => qualityScore(b) - qualityScore(a))
        .slice(0, 10);
      
      result.push({
        section: 'cold_start',
        title: '💎 Highest Signal (Cold Start)',
        subtitle: 'Top quality content — click to personalize',
        why: 'Showing global quality ranking because no preferences detected yet.',
        episodes: highSignal,
      });
    } else {
      // Personalized: Category-matched
      const categoryMatched = availableEpisodes
        .filter(ep => {
          const epCats = ep.categories?.major || [];
          return epCats.some(cat => categoryPrefs[cat]);
        })
        .sort((a, b) => {
          // Score by category match strength + quality
          const aMatch = (a.categories?.major || []).reduce((sum, cat) => sum + (categoryPrefs[cat] || 0), 0);
          const bMatch = (b.categories?.major || []).reduce((sum, cat) => sum + (categoryPrefs[cat] || 0), 0);
          return (bMatch + qualityScore(b)) - (aMatch + qualityScore(a));
        })
        .slice(0, 10);
      
      result.push({
        section: 'insights_for_you',
        title: '📊 Insights for You',
        subtitle: `Based on ${inferred.topCategories.slice(0, 2).map(([c]) => c).join(', ')}`,
        why: `Matching your inferred interests: ${inferred.topCategories.map(([c, s]) => `${c} (+${s})`).join(', ')}`,
        episodes: categoryMatched,
      });
    }
    
    // === SECTION 2: Highest Signal This Week ===
    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    const recentHighSignal = availableEpisodes
      .filter(ep => {
        if (!ep.published_at) return true;
        return new Date(ep.published_at) >= weekAgo;
      })
      .sort((a, b) => qualityScore(b) - qualityScore(a))
      .slice(0, 10);
    
    result.push({
      section: 'highest_signal',
      title: '💎 Highest Signal This Week',
      subtitle: 'Top Insight + Credibility scores',
      why: 'Ranked by quality score: 45% insight + 40% credibility + 15% information',
      episodes: recentHighSignal,
    });
    
    // === SECTION 3: Non-Consensus Ideas ===
    const contrarian = availableEpisodes
      .filter(ep => {
        // Has critical views data
        if (ep.critical_views?.has_critical_views) return true;
        // Or heuristic: high insight + credibility, low entertainment
        const s = ep.scores || {};
        return s.insight >= 3 && s.credibility >= 3 && (s.entertainment || 3) <= 2;
      })
      .sort((a, b) => {
        // Prioritize real critical views
        const aReal = a.critical_views?.has_critical_views ? 10 : 0;
        const bReal = b.critical_views?.has_critical_views ? 10 : 0;
        return (bReal + qualityScore(b)) - (aReal + qualityScore(a));
      })
      .slice(0, 8);
    
    result.push({
      section: 'non_consensus',
      title: '🔥 Non-Consensus Ideas',
      subtitle: 'Contrarian views from credible speakers',
      why: 'Episodes with critical_views data marked "highly non-consensus" + heuristic (high insight, high credibility, low entertainment)',
      episodes: contrarian,
    });
    
    // === SECTION 4: New from Your Shows (only if subscriptions) ===
    if (subscribedSeriesIds.size > 0) {
      const fromSubscribed = availableEpisodes
        .filter(ep => subscribedSeriesIds.has(ep.series?.id))
        .sort((a, b) => {
          const aDate = new Date(a.published_at || 0);
          const bDate = new Date(b.published_at || 0);
          return bDate - aDate;
        })
        .slice(0, 8);
      
      if (fromSubscribed.length > 0) {
        result.push({
          section: 'new_from_shows',
          title: '📡 New from Your Shows',
          subtitle: `Latest from ${inferred.implicitSubscriptions.map(s => s.name).slice(0, 2).join(', ')}`,
          why: `You clicked 2+ episodes from these series, so we treat them as implicit subscriptions.`,
          episodes: fromSubscribed,
        });
      }
    }
    
    // === SECTION 5: Trending in Category (only if category preference) ===
    if (topCategory) {
      const seriesPopularity = {};
      allSeries.forEach(s => {
        seriesPopularity[s.id] = s.popularity || s.serafis_score || 50;
      });
      
      const trending = availableEpisodes
        .filter(ep => (ep.categories?.major || []).includes(topCategory))
        .sort((a, b) => {
          const aPop = seriesPopularity[a.series?.id] || 50;
          const bPop = seriesPopularity[b.series?.id] || 50;
          return (bPop * 0.5 + qualityScore(b) * 0.3) - (aPop * 0.5 + qualityScore(a) * 0.3);
        })
        .slice(0, 8);
      
      result.push({
        section: 'trending',
        title: `🌟 Trending in ${topCategory}`,
        subtitle: 'Popular from top-rated series',
        why: `Episodes in ${topCategory} ranked by: 50% series popularity + 30% quality + 20% recency`,
        episodes: trending,
      });
    }
    
    return result;
  }, [availableEpisodes, allSeries, session, inferred]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse flex flex-col items-center gap-3">
          <div className="w-12 h-12 bg-indigo-500 rounded-full animate-bounce"></div>
          <p className="text-slate-400">Loading episodes...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="text-center max-w-md">
          <div className="text-4xl mb-4">⚠️</div>
          <p className="text-red-400 mb-2">{error}</p>
          <p className="text-slate-500 text-sm mb-4">
            Run in terminal:
          </p>
          <code className="block bg-slate-800 px-4 py-2 rounded text-sm text-green-400">
            cd mock_api && python3 server.py
          </code>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen pb-8">
      {/* Cold start banner */}
      {session.clicks.length < 2 && (
        <div className="mx-4 my-4 p-4 bg-blue-500/20 border border-blue-500/30 rounded-lg">
          <p className="text-blue-300 font-medium">🥶 Cold Start Mode</p>
          <p className="text-sm text-blue-400 mt-1">
            Click on episodes to reveal your preferences. Recommendations will personalize after 2+ clicks.
          </p>
        </div>
      )}
      
      {/* Recommendation Sections */}
      <div className="pt-2">
        {sections.map((section) => (
          <RecommendationSection
            key={section.section}
            section={section}
            onEpisodeClick={onEpisodeClick}
            onNotInterested={onNotInterested}
            onSave={onSave}
          />
        ))}
      </div>
      
      {sections.length === 0 && (
        <div className="text-center py-12">
          <p className="text-slate-500">No recommendations available</p>
        </div>
      )}
    </div>
  );
}
