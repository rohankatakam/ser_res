/**
 * Serafis Recommendation Engine Testing Harness
 * 
 * V1.1 - Session Pool with Progressive Reveal (Option C)
 * 
 * Three Pages:
 * 1. Browse - All catalog sorted by popularity
 * 2. For You - Personalized recommendations
 * 3. Developer - Debug view with algorithm details
 */

import { useState, useCallback, useMemo } from 'react';
import BrowsePage from './components/BrowsePage';
import ForYouPage from './components/ForYouPage';
import DevPage from './components/DevPage';
import EpisodeDetailPage from './components/EpisodeDetailPage';
import { engageEpisode } from './api';

function App() {
  // Current tab: 'browse', 'foryou', 'dev'
  const [currentTab, setCurrentTab] = useState('foryou');
  
  // Detail view state
  const [selectedEpisode, setSelectedEpisode] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  
  // Active recommendation session
  const [activeSessionId, setActiveSessionId] = useState(null);
  
  // Session state tracking user activity (resets on page refresh)
  const [session, setSession] = useState({
    engagements: [],
    notInterestedEpisodes: [],
    categoryInterests: {},
    seriesInterests: {},
  });
  
  // Computed values
  const viewedEpisodes = useMemo(() => 
    session.engagements.filter(e => e.type === 'click'),
    [session.engagements]
  );
  
  const bookmarkedEpisodes = useMemo(() => 
    session.engagements.filter(e => e.type === 'bookmark'),
    [session.engagements]
  );
  
  const excludedIds = useMemo(() => {
    const ids = new Set();
    session.engagements.forEach(eng => {
      const ep = eng.episode;
      if (ep) {
        ids.add(ep.content_id || ep.id);
        ids.add(ep.id);
      }
    });
    session.notInterestedEpisodes.forEach(ep => {
      ids.add(ep.content_id || ep.id);
      ids.add(ep.id);
    });
    return ids;
  }, [session]);
  
  const engagementsForApi = useMemo(() => 
    session.engagements.map(eng => ({
      episode_id: eng.episode?.id || eng.episode?.content_id,
      type: eng.type,
      timestamp: eng.timestamp
    })),
    [session.engagements]
  );
  
  const inferredPreferences = useMemo(() => {
    const categories = { ...session.categoryInterests };
    const series = { ...session.seriesInterests };
    
    const topCategories = Object.entries(categories)
      .filter(([_, score]) => score > 0)
      .sort((a, b) => b[1] - a[1]);
    
    const excludedCategories = Object.entries(categories)
      .filter(([_, score]) => score < 0)
      .map(([cat]) => cat);
    
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
  
  // Handle episode CLICK
  const handleView = useCallback((episode) => {
    const now = new Date().toISOString();
    
    if (activeSessionId && episode.id) {
      engageEpisode(activeSessionId, episode.id, 'click').catch(err => {
        console.warn('Failed to record engagement in session:', err);
      });
    }
    
    setSession(prev => {
      const alreadyClicked = prev.engagements.some(
        eng => eng.type === 'click' && 
        (eng.episode?.id === episode.id || eng.episode?.content_id === episode.content_id)
      );
      
      if (alreadyClicked) return prev;
      
      const newCategories = { ...prev.categoryInterests };
      const newSeries = { ...prev.seriesInterests };
      
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
      
      return {
        ...prev,
        engagements: [...prev.engagements, { episode, type: 'click', timestamp: now }],
        categoryInterests: newCategories,
        seriesInterests: newSeries,
      };
    });
    
    setSelectedEpisode(episode);
    setShowDetail(true);
  }, [activeSessionId]);
  
  // Handle BOOKMARK
  const handleBookmark = useCallback((episode) => {
    const now = new Date().toISOString();
    
    if (activeSessionId && episode.id) {
      engageEpisode(activeSessionId, episode.id, 'bookmark').catch(console.warn);
    }
    
    setSession(prev => {
      const alreadyBookmarked = prev.engagements.some(
        eng => eng.type === 'bookmark' && 
        (eng.episode?.id === episode.id || eng.episode?.content_id === episode.content_id)
      );
      
      if (alreadyBookmarked) return prev;
      
      const newCategories = { ...prev.categoryInterests };
      if (episode.categories?.major) {
        episode.categories.major.forEach(cat => {
          newCategories[cat] = (newCategories[cat] || 0) + 2;
        });
      }
      
      return {
        ...prev,
        engagements: [...prev.engagements, { episode, type: 'bookmark', timestamp: now }],
        categoryInterests: newCategories,
      };
    });
  }, [activeSessionId]);
  
  // Handle NOT INTERESTED
  const handleNotInterested = useCallback((episode) => {
    setSession(prev => {
      const newCategories = { ...prev.categoryInterests };
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
  
  const handleSessionChange = useCallback((sessionId) => {
    setActiveSessionId(sessionId);
  }, []);
  
  const handleBackFromDetail = useCallback(() => {
    setShowDetail(false);
    setSelectedEpisode(null);
  }, []);
  
  const handleReset = useCallback(() => {
    setSession({
      engagements: [],
      notInterestedEpisodes: [],
      categoryInterests: {},
      seriesInterests: {},
    });
    setActiveSessionId(null);
    setShowDetail(false);
    setSelectedEpisode(null);
  }, []);
  
  // Show detail page overlay
  if (showDetail && selectedEpisode) {
    return (
      <div className="min-h-screen bg-slate-900">
        <EpisodeDetailPage
          episode={selectedEpisode}
          onBack={handleBackFromDetail}
          onBookmark={handleBookmark}
        />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-slate-900">
      {/* Tab Bar */}
      <nav className="sticky top-0 z-20 bg-slate-900 border-b border-slate-700">
        <div className="max-w-4xl mx-auto px-4">
          <div className="flex items-center justify-between h-14">
            <div className="flex gap-1">
              <TabButton 
                active={currentTab === 'browse'} 
                onClick={() => setCurrentTab('browse')}
              >
                Browse
              </TabButton>
              <TabButton 
                active={currentTab === 'foryou'} 
                onClick={() => setCurrentTab('foryou')}
                badge={inferredPreferences.totalEngagements > 0 ? inferredPreferences.totalEngagements : null}
              >
                For You
              </TabButton>
              <TabButton 
                active={currentTab === 'dev'} 
                onClick={() => setCurrentTab('dev')}
              >
                Developer
              </TabButton>
            </div>
            <button
              onClick={handleReset}
              className="px-3 py-1.5 text-sm bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
            >
              Reset
            </button>
          </div>
        </div>
      </nav>
      
      {/* Page Content */}
      <main className="max-w-4xl mx-auto">
        {currentTab === 'browse' && (
          <BrowsePage
            onView={handleView}
            onBookmark={handleBookmark}
            excludedIds={excludedIds}
          />
        )}
        {currentTab === 'foryou' && (
          <ForYouPage
            engagements={engagementsForApi}
            excludedIds={excludedIds}
            activeSessionId={activeSessionId}
            onSessionChange={handleSessionChange}
            onView={handleView}
            onBookmark={handleBookmark}
            onNotInterested={handleNotInterested}
          />
        )}
        {currentTab === 'dev' && (
          <DevPage
            session={session}
            inferred={inferredPreferences}
            activeSessionId={activeSessionId}
            viewedEpisodes={viewedEpisodes}
            bookmarkedEpisodes={bookmarkedEpisodes}
            onReset={handleReset}
          />
        )}
      </main>
    </div>
  );
}

function TabButton({ children, active, onClick, badge }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors relative ${
        active 
          ? 'bg-indigo-600 text-white' 
          : 'text-slate-400 hover:text-white hover:bg-slate-800'
      }`}
    >
      {children}
      {badge && (
        <span className="absolute -top-1 -right-1 w-5 h-5 bg-indigo-500 text-white text-xs rounded-full flex items-center justify-center">
          {badge}
        </span>
      )}
    </button>
  );
}

export default App;
