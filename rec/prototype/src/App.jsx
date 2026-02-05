/**
 * Serafis Recommendation Engine Testing Harness
 * 
 * V1.1 - Session Pool with Progressive Reveal (Option C)
 * 
 * Feed Behavior:
 * - On load: Create session with ranked queue of all candidates
 * - Load More: Return next 10 from queue (no recomputation)
 * - Refresh: Create new session with fresh computation from latest engagements
 * - Engage: Mark episode as engaged, exclude from queue
 * 
 * Session persists within page session (no persistence across refreshes).
 */

import { useState, useCallback, useMemo } from 'react';
import DiscoverPage from './components/DiscoverPage';
import EpisodeDetailPage from './components/EpisodeDetailPage';
import SessionPanel from './components/SessionPanel';
import { engageEpisode } from './api';

function App() {
  // Current view: 'feed' or 'detail'
  const [currentView, setCurrentView] = useState('feed');
  const [selectedEpisode, setSelectedEpisode] = useState(null);
  
  // Active recommendation session
  const [activeSessionId, setActiveSessionId] = useState(null);
  
  // Session state tracking user activity (resets on page refresh)
  const [session, setSession] = useState({
    // Engagement history with timestamps - used to build user activity vector
    engagements: [],         // [{episode, type: 'click'|'bookmark', timestamp}]
    
    // User "not interested" - excluded from recommendations
    notInterestedEpisodes: [],
    
    // Inferred from interactions (for display purposes)
    categoryInterests: {},   // { "Technology & AI": 3, "Crypto": -1 }
    seriesInterests: {},     // { "series_id": { name, count } }
  });
  
  const [refreshKey, setRefreshKey] = useState(0);
  const [showPanel, setShowPanel] = useState(true);
  
  // Computed: viewed episodes (clicks)
  const viewedEpisodes = useMemo(() => 
    session.engagements.filter(e => e.type === 'click'),
    [session.engagements]
  );
  
  // Computed: bookmarked episodes
  const bookmarkedEpisodes = useMemo(() => 
    session.engagements.filter(e => e.type === 'bookmark'),
    [session.engagements]
  );
  
  // All episode IDs that should be EXCLUDED from recommendations
  const excludedIds = useMemo(() => {
    const ids = new Set();
    
    // All engaged episodes (clicks and bookmarks)
    session.engagements.forEach(eng => {
      const ep = eng.episode;
      if (ep) {
        ids.add(ep.content_id || ep.id);
        ids.add(ep.id);
      }
    });
    
    // Not interested episodes
    session.notInterestedEpisodes.forEach(ep => {
      ids.add(ep.content_id || ep.id);
      ids.add(ep.id);
    });
    
    return ids;
  }, [session]);
  
  // Engagements in API format (for sending to backend)
  const engagementsForApi = useMemo(() => 
    session.engagements.map(eng => ({
      episode_id: eng.episode?.id || eng.episode?.content_id,
      type: eng.type,
      timestamp: eng.timestamp
    })),
    [session.engagements]
  );
  
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
      totalViewed: viewedEpisodes.length,
      totalBookmarked: bookmarkedEpisodes.length,
      totalEngagements: session.engagements.length,
      totalExcluded: excludedIds.size,
    };
  }, [session, viewedEpisodes, bookmarkedEpisodes, excludedIds]);
  
  // Handle episode CLICK - records engagement, opens detail page
  const handleView = useCallback((episode) => {
    const now = new Date().toISOString();
    
    // Also notify backend session about the engagement
    if (activeSessionId && episode.id) {
      engageEpisode(activeSessionId, episode.id, 'click').catch(err => {
        console.warn('Failed to record engagement in session:', err);
      });
    }
    
    setSession(prev => {
      // Check if already engaged (prevent duplicate engagements of same type)
      const alreadyClicked = prev.engagements.some(
        eng => eng.type === 'click' && 
        (eng.episode?.id === episode.id || eng.episode?.content_id === episode.content_id)
      );
      
      if (alreadyClicked) {
        // Still show the detail page, but don't record duplicate
        return prev;
      }
      
      const newCategories = { ...prev.categoryInterests };
      const newSeries = { ...prev.seriesInterests };
      
      // Learn from viewed content (click = weight 1)
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
      
      // Record engagement
      const engagement = {
        episode: episode,
        type: 'click',
        timestamp: now,
      };
      
      return {
        ...prev,
        engagements: [...prev.engagements, engagement],
        categoryInterests: newCategories,
        seriesInterests: newSeries,
      };
    });
    
    // Navigate to detail page
    setSelectedEpisode(episode);
    setCurrentView('detail');
  }, [activeSessionId]);
  
  // Handle BOOKMARK - strong signal, stays on current page
  const handleBookmark = useCallback((episode) => {
    const now = new Date().toISOString();
    
    // Notify backend session
    if (activeSessionId && episode.id) {
      engageEpisode(activeSessionId, episode.id, 'bookmark').catch(err => {
        console.warn('Failed to record bookmark in session:', err);
      });
    }
    
    setSession(prev => {
      // Check if already bookmarked
      const alreadyBookmarked = prev.engagements.some(
        eng => eng.type === 'bookmark' && 
        (eng.episode?.id === episode.id || eng.episode?.content_id === episode.content_id)
      );
      
      if (alreadyBookmarked) {
        return prev;
      }
      
      const newCategories = { ...prev.categoryInterests };
      
      // Bookmarks are strong positive signals (weight = 2)
      if (episode.categories?.major) {
        episode.categories.major.forEach(cat => {
          newCategories[cat] = (newCategories[cat] || 0) + 2;
        });
      }
      
      // Record engagement
      const engagement = {
        episode: episode,
        type: 'bookmark',
        timestamp: now,
      };
      
      return {
        ...prev,
        engagements: [...prev.engagements, engagement],
        categoryInterests: newCategories,
      };
    });
  }, [activeSessionId]);
  
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
  }, []);
  
  // Handle session ID change (from DiscoverPage)
  const handleSessionChange = useCallback((sessionId) => {
    setActiveSessionId(sessionId);
  }, []);
  
  // Navigate back to feed from detail page
  const handleBackToFeed = useCallback(() => {
    setCurrentView('feed');
    setSelectedEpisode(null);
  }, []);
  
  // Reset to fresh state (cold start)
  const handleReset = useCallback(() => {
    setSession({
      engagements: [],
      notInterestedEpisodes: [],
      categoryInterests: {},
      seriesInterests: {},
    });
    setActiveSessionId(null);
    setCurrentView('feed');
    setSelectedEpisode(null);
    setRefreshKey(k => k + 1);
  }, []);
  
  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="sticky top-0 z-20 bg-slate-900 border-b border-slate-700">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">
              {currentView === 'detail' ? 'Episode Details' : 'For You Feed'}
            </h1>
            <p className="text-xs text-slate-500">
              V1.1 Session Pool • {inferredPreferences.totalEngagements} engagements • 
              {activeSessionId ? ` Session: ${activeSessionId}` : ' No session'}
            </p>
          </div>
          <div className="flex gap-2">
            {currentView === 'feed' && (
              <button
                onClick={() => setShowPanel(!showPanel)}
                className="px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded hover:bg-slate-600"
              >
                {showPanel ? 'Hide' : 'Show'} State
              </button>
            )}
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
        <div className={`flex-1 ${currentView === 'feed' && showPanel ? 'mr-80' : ''}`}>
          {currentView === 'detail' ? (
            <EpisodeDetailPage
              episode={selectedEpisode}
              onBack={handleBackToFeed}
              onBookmark={handleBookmark}
            />
          ) : (
            <DiscoverPage
              key={refreshKey}
              excludedIds={excludedIds}
              inferred={inferredPreferences}
              viewedEpisodes={viewedEpisodes}
              bookmarkedEpisodes={bookmarkedEpisodes}
              engagements={engagementsForApi}
              activeSessionId={activeSessionId}
              onSessionChange={handleSessionChange}
              onView={handleView}
              onBookmark={handleBookmark}
              onNotInterested={handleNotInterested}
            />
          )}
        </div>
        
        {/* Session panel (only on feed view) */}
        {currentView === 'feed' && showPanel && (
          <SessionPanel
            session={session}
            inferred={inferredPreferences}
            activeSessionId={activeSessionId}
            onReset={handleReset}
          />
        )}
      </div>
    </div>
  );
}

export default App;
