/**
 * Serafis Evaluation Framework Testing Harness
 * 
 * V2.1 - Simplified UI
 * 
 * Pages:
 * 1. Browse - All catalog sorted by popularity
 * 2. For You - Personalized recommendations
 * 3. Developer - Debug view with sub-tabs:
 *    - Insights: Algorithm details and session debugging
 *    - Tests: Run and view evaluation test results
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import BrowsePage from './components/BrowsePage';
import ForYouPage from './components/ForYouPage';
import DevPage from './components/DevPage';
import EpisodeDetailPage from './components/EpisodeDetailPage';
import LoginScreen from './components/LoginScreen';
import { engageEpisode, getApiKeyStatus, getEngagements, resetEngagements } from './api';

const USER_STORAGE_KEY = 'serafis_user';

function App() {
  // Current user (from login / create). Persisted in localStorage.
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  // Current tab: 'browse', 'foryou', 'dev'
  const [currentTab, setCurrentTab] = useState('foryou');

  // Detail view state
  const [selectedEpisode, setSelectedEpisode] = useState(null);
  const [showDetail, setShowDetail] = useState(false);

  // Active recommendation session
  const [activeSessionId, setActiveSessionId] = useState(null);

  // API key status
  const [apiKeyStatus, setApiKeyStatus] = useState(null);

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

  // Check API key status on mount
  useEffect(() => {
    const checkApiKeys = async () => {
      try {
        const status = await getApiKeyStatus();
        setApiKeyStatus(status);
      } catch (err) {
        console.error('Failed to check API key status:', err);
        // Don't block the app if the check fails
      }
    };

    checkApiKeys();
  }, []);

  // Load engagements from backend when user is set (Firestore sync)
  useEffect(() => {
    if (!currentUser?.user_id) return;
    let cancelled = false;
    console.log('[App] Fetching engagements from backend (Firestore) for user:', currentUser.user_id);
    getEngagements(currentUser.user_id)
      .then(({ engagements }) => {
        console.log('[App] Engagements from backend (Firestore):', { count: engagements?.length ?? 0, userId: currentUser.user_id });
        if (cancelled || !engagements?.length) return;
        setSession(prev => ({
          ...prev,
          engagements: engagements.map(e => ({
            episode_id: e.episode_id,
            type: e.type || 'click',
            timestamp: e.timestamp || '',
            episode: { id: e.episode_id, content_id: e.episode_id }
          }))
        }));
      })
      .catch(err => console.warn('[App] Failed to load engagements (Firestore):', err));
    return () => { cancelled = true; };
  }, [currentUser?.user_id]);

  // Handle episode CLICK
  const handleView = useCallback((episode) => {
    const now = new Date().toISOString();

    if (activeSessionId && episode.id) {
      engageEpisode(activeSessionId, episode.id, 'click', currentUser?.user_id ?? currentUser?.id ?? null).catch(err => {
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
  }, [activeSessionId, currentUser?.user_id]);

  // Handle BOOKMARK
  const handleBookmark = useCallback((episode) => {
    const now = new Date().toISOString();

    if (activeSessionId && episode.id) {
      engageEpisode(activeSessionId, episode.id, 'bookmark', currentUser?.user_id ?? currentUser?.id ?? null).catch(console.warn);
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
  }, [activeSessionId, currentUser?.user_id]);

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

  const handleUserSuccess = useCallback((user) => {
    setCurrentUser(user);
    try {
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    } catch (e) {
      console.warn('Could not persist user to localStorage', e);
    }
  }, []);

  const handleLogout = useCallback(() => {
    setCurrentUser(null);
    try {
      localStorage.removeItem(USER_STORAGE_KEY);
    } catch (e) {}
    setActiveSessionId(null);
    setSession({
      engagements: [],
      notInterestedEpisodes: [],
      categoryInterests: {},
      seriesInterests: {},
    });
  }, []);

  const handleSessionChange = useCallback((sessionId) => {
    setActiveSessionId(sessionId);
  }, []);

  // Login gate: show LoginScreen until user enters or creates account
  if (!currentUser) {
    return (
      <LoginScreen onSuccess={handleUserSuccess} />
    );
  }

  const handleBackFromDetail = useCallback(() => {
    setShowDetail(false);
    setSelectedEpisode(null);
  }, []);

  const handleReset = useCallback(async () => {
    if (currentUser?.user_id) {
      try {
        await resetEngagements(currentUser.user_id);
      } catch (err) {
        console.warn('Reset API failed:', err);
      }
    }
    setSession({
      engagements: [],
      notInterestedEpisodes: [],
      categoryInterests: {},
      seriesInterests: {},
    });
    setActiveSessionId(null);
    setShowDetail(false);
    setSelectedEpisode(null);
  }, [currentUser?.user_id]);

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
      {/* OpenAI API Key Error Banner */}
      {apiKeyStatus && !apiKeyStatus.openai_configured && (
        <div className="bg-red-600/20 border-b border-red-600/50 px-4 py-3">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-start gap-3">
              <span className="text-xl">⚠️</span>
              <div className="flex-1">
                <p className="text-red-300 font-semibold mb-1">
                  OpenAI API Key Required
                </p>
                <p className="text-red-200/80 text-sm">
                  Add your OpenAI API key to the <code className="bg-red-900/30 px-1.5 py-0.5 rounded text-red-200">.env</code> file in the project root, then rebuild and restart:
                </p>
                <pre className="mt-2 bg-slate-800/50 p-2 rounded text-xs text-slate-300 font-mono overflow-x-auto">
                  docker-compose down && docker-compose up --build -d
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}


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
              <span className="text-slate-400 text-sm">
                {currentUser.display_name}
              </span>
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 text-sm bg-slate-700 text-slate-300 rounded hover:bg-slate-600"
              >
                Logout
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
            userId={currentUser?.user_id ?? null}
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
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors relative ${active
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
