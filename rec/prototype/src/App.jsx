/**
 * Serafis Evaluation Framework Testing Harness
 * 
 * V2.0 - Full Evaluation Framework with Tests UI
 * 
 * Pages:
 * 1. Browse - All catalog sorted by popularity
 * 2. For You - Personalized recommendations
 * 3. Developer - Debug view with sub-tabs:
 *    - Insights: Algorithm details and session debugging
 *    - Tests: Run and view evaluation test results
 */

import { useState, useCallback, useMemo } from 'react';
import BrowsePage from './components/BrowsePage';
import ForYouPage from './components/ForYouPage';
import DevPage from './components/DevPage';
import EpisodeDetailPage from './components/EpisodeDetailPage';
import SettingsModal from './components/SettingsModal';
import { engageEpisode } from './api';

function App() {
  // Current tab: 'browse', 'foryou', 'dev'
  const [currentTab, setCurrentTab] = useState('foryou');
  
  // Detail view state
  const [selectedEpisode, setSelectedEpisode] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  
  // Active recommendation session
  const [activeSessionId, setActiveSessionId] = useState(null);
  
  // Settings modal state - persist API keys to localStorage
  const [showSettings, setShowSettings] = useState(false);
  const [geminiKey, setGeminiKey] = useState(() => localStorage.getItem('serafis_gemini_key') || '');
  const [openaiKey, setOpenaiKey] = useState(() => localStorage.getItem('serafis_openai_key') || '');
  const [configLoaded, setConfigLoaded] = useState(false);
  
  // Persist API keys to localStorage when they change
  const handleGeminiKeyChange = useCallback((key) => {
    setGeminiKey(key);
    localStorage.setItem('serafis_gemini_key', key);
  }, []);
  
  const handleOpenaiKeyChange = useCallback((key) => {
    setOpenaiKey(key);
    localStorage.setItem('serafis_openai_key', key);
  }, []);
  
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
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSettings(true)}
                className="px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded hover:bg-slate-600 flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Settings
              </button>
              <button
                onClick={handleReset}
                className="px-3 py-1.5 text-sm bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
              >
                Reset
              </button>
            </div>
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
            geminiKey={geminiKey}
          />
        )}
      </main>
      
      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        geminiKey={geminiKey}
        onGeminiKeyChange={handleGeminiKeyChange}
        openaiKey={openaiKey}
        onOpenaiKeyChange={handleOpenaiKeyChange}
        onConfigLoaded={(result) => {
          setConfigLoaded(true);
          setShowSettings(false);
        }}
      />
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
