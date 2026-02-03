/**
 * Serafis Recommendation Engine Tester
 * 
 * Core principle: Recommendations show content user has NOT interacted with.
 * 
 * User signals:
 * - View/Play (click) → Mark as seen → EXCLUDE from recommendations
 * - Bookmark → Mark as saved → EXCLUDE from recommendations  
 * - Not Interested → EXCLUDE + negative signal
 * - Category interests → Inferred from interactions
 */

import { useState, useCallback, useMemo } from 'react';
import DiscoverPage from './components/DiscoverPage';
import SessionPanel from './components/SessionPanel';

function App() {
  // Session state tracking user activity
  const [session, setSession] = useState({
    // User activity (viewed episodes) - these get EXCLUDED
    viewedEpisodes: [],      // Episodes user has clicked/played
    
    // User bookmarks - also EXCLUDED (already discovered)
    bookmarkedEpisodes: [],
    
    // User "not interested" - EXCLUDED + negative signal
    notInterestedEpisodes: [],
    
    // Inferred from interactions
    categoryInterests: {},   // { "Technology & AI": 3, "Crypto": -1 }
    seriesInterests: {},     // { "series_id": { name, count } }
  });
  
  const [refreshKey, setRefreshKey] = useState(0);
  const [showPanel, setShowPanel] = useState(true);
  
  // All episode IDs that should be EXCLUDED from recommendations
  const excludedIds = useMemo(() => {
    const ids = new Set();
    // viewedEpisodes and bookmarkedEpisodes now have { episode, timestamp } structure
    session.viewedEpisodes.forEach(item => {
      const ep = item.episode || item;
      ids.add(ep.content_id || ep.id);
    });
    session.bookmarkedEpisodes.forEach(item => {
      const ep = item.episode || item;
      ids.add(ep.content_id || ep.id);
    });
    session.notInterestedEpisodes.forEach(ep => ids.add(ep.content_id || ep.id));
    return ids;
  }, [session]);
  
  // Calculate inferred preferences
  const inferredPreferences = useMemo(() => {
    const categories = { ...session.categoryInterests };
    const series = { ...session.seriesInterests };
    
    // Sort categories by interest score
    const topCategories = Object.entries(categories)
      .filter(([_, score]) => score > 0)
      .sort((a, b) => b[1] - a[1]);
    
    const excludedCategories = Object.entries(categories)
      .filter(([_, score]) => score < 0)
      .map(([cat]) => cat);
    
    // Series with 2+ views = implicit subscription
    const implicitSubscriptions = Object.entries(series)
      .filter(([_, data]) => data.count >= 2)
      .map(([id, data]) => ({ id, ...data }));
    
    return {
      topCategories,
      excludedCategories,
      implicitSubscriptions,
      totalViewed: session.viewedEpisodes.length,
      totalBookmarked: session.bookmarkedEpisodes.length,
      totalExcluded: excludedIds.size,
    };
  }, [session, excludedIds]);
  
  // Handle episode VIEW (click/play) - marks as seen, learns preferences
  const handleView = useCallback((episode) => {
    setSession(prev => {
      // Check if already viewed (prevent duplicates)
      const alreadyViewed = prev.viewedEpisodes.some(
        item => (item.episode?.content_id || item.episode?.id) === (episode.content_id || episode.id)
      );
      if (alreadyViewed) return prev;
      
      const newCategories = { ...prev.categoryInterests };
      const newSeries = { ...prev.seriesInterests };
      
      // Learn from viewed content
      if (episode.categories?.major) {
        episode.categories.major.forEach(cat => {
          newCategories[cat] = (newCategories[cat] || 0) + 1;
        });
      }
      
      if (episode.series?.id) {
        newSeries[episode.series.id] = {
          name: episode.series.name,
          count: (newSeries[episode.series.id]?.count || 0) + 1
        };
      }
      
      // Store with timestamp for history tracking
      const viewedItem = {
        episode: episode,
        timestamp: new Date().toISOString(),
      };
      
      return {
        ...prev,
        viewedEpisodes: [...prev.viewedEpisodes, viewedItem],
        categoryInterests: newCategories,
        seriesInterests: newSeries,
      };
    });
    setRefreshKey(k => k + 1);
  }, []);
  
  // Handle BOOKMARK - marks as saved (strong interest), excludes from recs
  const handleBookmark = useCallback((episode) => {
    setSession(prev => {
      // Check if already bookmarked (prevent duplicates)
      const alreadyBookmarked = prev.bookmarkedEpisodes.some(
        item => (item.episode?.content_id || item.episode?.id) === (episode.content_id || episode.id)
      );
      if (alreadyBookmarked) return prev;
      
      const newCategories = { ...prev.categoryInterests };
      
      // Bookmarks are strong positive signals (weight = 2)
      if (episode.categories?.major) {
        episode.categories.major.forEach(cat => {
          newCategories[cat] = (newCategories[cat] || 0) + 2;
        });
      }
      
      // Store with timestamp for history tracking
      const bookmarkedItem = {
        episode: episode,
        timestamp: new Date().toISOString(),
      };
      
      return {
        ...prev,
        bookmarkedEpisodes: [...prev.bookmarkedEpisodes, bookmarkedItem],
        categoryInterests: newCategories,
      };
    });
    setRefreshKey(k => k + 1);
  }, []);
  
  // Handle NOT INTERESTED - excludes + negative signal
  const handleNotInterested = useCallback((episode) => {
    setSession(prev => {
      const newCategories = { ...prev.categoryInterests };
      
      // Negative signal for categories
      if (episode.categories?.major) {
        episode.categories.major.forEach(cat => {
          newCategories[cat] = (newCategories[cat] || 0) - 1;
        });
      }
      
      return {
        ...prev,
        notInterestedEpisodes: [...prev.notInterestedEpisodes, episode],
        categoryInterests: newCategories,
      };
    });
    setRefreshKey(k => k + 1);
  }, []);
  
  // Reset to fresh state
  const handleReset = useCallback(() => {
    setSession({
      viewedEpisodes: [],
      bookmarkedEpisodes: [],
      notInterestedEpisodes: [],
      categoryInterests: {},
      seriesInterests: {},
    });
    setRefreshKey(k => k + 1);
  }, []);
  
  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-slate-900 border-b border-slate-700">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Recommendations</h1>
            <p className="text-xs text-slate-500">
              {inferredPreferences.totalExcluded} episodes excluded • Showing unseen content only
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowPanel(!showPanel)}
              className="px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded hover:bg-slate-600"
            >
              {showPanel ? 'Hide' : 'Show'} State
            </button>
            <button
              onClick={handleReset}
              className="px-3 py-1.5 text-sm bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
            >
              Reset
            </button>
          </div>
        </div>
      </header>
      
      <div className="max-w-6xl mx-auto flex">
        {/* Main content */}
        <div className={`flex-1 ${showPanel ? 'mr-80' : ''}`}>
          <DiscoverPage
            key={refreshKey}
            excludedIds={excludedIds}
            inferred={inferredPreferences}
            viewedEpisodes={session.viewedEpisodes}
            bookmarkedEpisodes={session.bookmarkedEpisodes}
            onView={handleView}
            onBookmark={handleBookmark}
            onNotInterested={handleNotInterested}
          />
        </div>
        
        {/* Session panel */}
        {showPanel && (
          <SessionPanel
            session={session}
            inferred={inferredPreferences}
            onReset={handleReset}
          />
        )}
      </div>
    </div>
  );
}

export default App;
