/**
 * Serafis Recommendation Engine Tester
 * 
 * Interactive testing environment for the recommendation algorithms.
 * Starts cold, learns from interactions, shows transparent algorithm state.
 */

import { useState, useCallback } from 'react';
import DiscoverPage from './components/DiscoverPage';
import SessionPanel from './components/SessionPanel';

function App() {
  // Session state - starts empty (cold start)
  const [session, setSession] = useState({
    clicks: [],           // Episodes clicked/played
    notInterested: [],    // Episodes marked not interested
    saves: [],            // Episodes bookmarked
    categoryAffinities: {},  // Inferred category preferences
    seriesAffinities: {},    // Inferred series preferences
    qualityPreference: 0,    // Learned quality threshold
  });
  
  const [refreshKey, setRefreshKey] = useState(0);
  const [showPanel, setShowPanel] = useState(true);
  
  // Calculate inferred preferences from session
  const getInferredPreferences = useCallback(() => {
    const categories = {};
    const series = {};
    let totalInsight = 0;
    let clickCount = 0;
    
    session.clicks.forEach(ep => {
      // Track category affinities
      if (ep.categories?.major) {
        ep.categories.major.forEach(cat => {
          categories[cat] = (categories[cat] || 0) + 1;
        });
      }
      // Track series affinities
      if (ep.series?.id) {
        series[ep.series.id] = {
          name: ep.series.name,
          count: (series[ep.series.id]?.count || 0) + 1
        };
      }
      // Track quality preference
      if (ep.scores?.insight) {
        totalInsight += ep.scores.insight;
        clickCount++;
      }
    });
    
    // Penalize categories from not interested
    session.notInterested.forEach(ep => {
      if (ep.categories?.major) {
        ep.categories.major.forEach(cat => {
          categories[cat] = (categories[cat] || 0) - 2;
        });
      }
    });
    
    // Sort categories by affinity
    const sortedCategories = Object.entries(categories)
      .sort((a, b) => b[1] - a[1])
      .filter(([_, count]) => count > 0);
    
    // Get top series (2+ clicks = implicit subscription)
    const implicitSubscriptions = Object.entries(series)
      .filter(([_, data]) => data.count >= 2)
      .map(([id, data]) => ({ id, ...data }));
    
    return {
      topCategories: sortedCategories.slice(0, 3),
      implicitSubscriptions,
      avgInsightClicked: clickCount > 0 ? (totalInsight / clickCount).toFixed(1) : null,
      excludedCategories: Object.entries(categories)
        .filter(([_, count]) => count < 0)
        .map(([cat]) => cat),
    };
  }, [session]);
  
  // Handle episode click (positive signal)
  const handleClick = useCallback((episode) => {
    setSession(prev => ({
      ...prev,
      clicks: [...prev.clicks, episode],
    }));
    setRefreshKey(k => k + 1);
  }, []);
  
  // Handle not interested (negative signal)
  const handleNotInterested = useCallback((episode) => {
    setSession(prev => ({
      ...prev,
      notInterested: [...prev.notInterested, episode],
    }));
    setRefreshKey(k => k + 1);
  }, []);
  
  // Handle save/bookmark (strong positive signal)
  const handleSave = useCallback((episode) => {
    setSession(prev => ({
      ...prev,
      saves: [...prev.saves, episode],
      clicks: prev.clicks.includes(episode) ? prev.clicks : [...prev.clicks, episode],
    }));
    setRefreshKey(k => k + 1);
  }, []);
  
  // Reset to cold start
  const handleReset = useCallback(() => {
    setSession({
      clicks: [],
      notInterested: [],
      saves: [],
      categoryAffinities: {},
      seriesAffinities: {},
      qualityPreference: 0,
    });
    setRefreshKey(k => k + 1);
  }, []);
  
  const inferred = getInferredPreferences();
  
  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-slate-900 border-b border-slate-700">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Serafis Recommendation Tester</h1>
            <p className="text-xs text-slate-500">
              Session: {session.clicks.length} clicks, {session.notInterested.length} excluded, {session.saves.length} saved
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowPanel(!showPanel)}
              className="px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded hover:bg-slate-600"
            >
              {showPanel ? 'Hide' : 'Show'} Session
            </button>
            <button
              onClick={handleReset}
              className="px-3 py-1.5 text-sm bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
            >
              Reset (Cold Start)
            </button>
          </div>
        </div>
      </header>
      
      <div className="max-w-6xl mx-auto flex">
        {/* Main content */}
        <div className={`flex-1 ${showPanel ? 'pr-80' : ''}`}>
          <DiscoverPage
            key={refreshKey}
            session={session}
            inferred={inferred}
            onEpisodeClick={handleClick}
            onNotInterested={handleNotInterested}
            onSave={handleSave}
          />
        </div>
        
        {/* Session panel */}
        {showPanel && (
          <SessionPanel
            session={session}
            inferred={inferred}
            onReset={handleReset}
          />
        )}
      </div>
    </div>
  );
}

export default App;
