/**
 * Developer Page - Debug & Algorithm Insights + Tests + Profiles
 * 
 * Three sub-tabs:
 * 1. Insights - Session state, engagement history, algorithm config
 * 2. Tests - Run and view evaluation test results
 * 3. Profiles - View evaluation profiles with full data
 */

import { useState, useEffect } from 'react';
import { fetchStats } from '../api';
import TestsPage from './TestsPage';
import ProfilesPage from './ProfilesPage';

export default function DevPage({
  session,
  inferred,
  activeSessionId,
  viewedEpisodes,
  bookmarkedEpisodes,
  onReset
}) {
  const [subTab, setSubTab] = useState('insights'); // 'insights', 'tests', or 'profiles'
  const [apiStats, setApiStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats()
      .then(setApiStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const engagements = session?.engagements || [];
  const notInterested = session?.notInterestedEpisodes || [];
  const categoryInterests = session?.categoryInterests || {};
  const seriesInterests = session?.seriesInterests || {};

  const sortedCategories = Object.entries(categoryInterests)
    .sort((a, b) => b[1] - a[1]);

  return (
    <div className="p-4 pb-8">
      {/* Header with Sub-tabs */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Developer View</h1>
          <p className="text-slate-400 text-sm">Algorithm insights, session debugging & tests</p>
        </div>
        <button
          onClick={onReset}
          className="px-4 py-2 bg-red-600/20 text-red-400 text-sm font-medium rounded-lg hover:bg-red-600/30"
        >
          Reset All Data
        </button>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-700 pb-4">
        <button
          onClick={() => setSubTab('insights')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${subTab === 'insights'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
        >
          Insights
        </button>
        <button
          onClick={() => setSubTab('tests')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${subTab === 'tests'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
        >
          Tests
        </button>
        <button
          onClick={() => setSubTab('profiles')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${subTab === 'profiles'
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
        >
          Profiles
        </button>
      </div>

      {/* Tests Sub-tab */}
      {subTab === 'tests' && (
        <TestsPage />
      )}

      {/* Profiles Sub-tab */}
      {subTab === 'profiles' && (
        <ProfilesPage />
      )}

      {/* Insights Sub-tab */}
      {subTab === 'insights' && (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total Engagements" value={inferred?.totalEngagements || 0} color="blue" />
            <StatCard label="Clicks" value={viewedEpisodes?.length || 0} color="indigo" />
            <StatCard label="Bookmarks" value={bookmarkedEpisodes?.length || 0} color="purple" />
            <StatCard label="Excluded" value={inferred?.totalExcluded || 0} color="red" />
          </div>

          {/* Session Info */}
          <Section title="Active Session">
            {activeSessionId ? (
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded">Active</span>
                  <span className="font-mono text-sm text-slate-300">{activeSessionId}</span>
                </div>
                <div className="text-sm text-slate-400 space-y-1">
                  <p>• Queue is deterministic within session</p>
                  <p>• "Load More" returns next N from queue (no recomputation)</p>
                  <p>• "Refresh" creates new session with fresh rankings</p>
                </div>
              </div>
            ) : (
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700 text-slate-500">
                No active session. Go to "For You" tab to create one.
              </div>
            )}
          </Section>

          {/* Algorithm Info */}
          <Section title="V1.1 Algorithm">
            <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Mode</span>
                  <span className="text-white">
                    {engagements.length === 0
                      ? 'Cold Start (Quality Ranking)'
                      : engagements.length < 2
                        ? 'Building Profile...'
                        : 'Personalized (Semantic Matching)'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">User Vector</span>
                  <span className="text-white">
                    {Math.min(engagements.length, 5)} episodes (max 5)
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Embedding Model</span>
                  <span className="text-white">text-embedding-3-small</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Similarity</span>
                  <span className="text-white">Cosine (title + key_insights)</span>
                </div>
              </div>
            </div>
          </Section>

          {/* API Stats */}
          <Section title="API Statistics">
            {loading ? (
              <div className="text-slate-500">Loading...</div>
            ) : apiStats ? (
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-slate-400">Episodes</span>
                    <p className="text-xl font-bold text-white">{apiStats.total_episodes}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Embeddings</span>
                    <p className="text-xl font-bold text-white">{apiStats.total_embeddings}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">High Quality (C+I≥5)</span>
                    <p className="text-xl font-bold text-yellow-400">{apiStats.high_quality_episodes}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Recent (30d)</span>
                    <p className="text-xl font-bold text-green-400">{apiStats.recent_episodes}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Contrarian</span>
                    <p className="text-xl font-bold text-orange-400">{apiStats.contrarian_episodes}</p>
                  </div>
                  <div>
                    <span className="text-slate-400">Active Sessions</span>
                    <p className="text-xl font-bold text-purple-400">{apiStats.active_sessions}</p>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-700">
                  <p className="text-xs text-slate-500 font-mono">
                    Config: C≥{apiStats.config?.credibility_floor}, C+I≥{apiStats.config?.combined_floor},
                    Freshness: {apiStats.config?.freshness_window_days}d, Pool: {apiStats.config?.candidate_pool_size}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-red-400">Failed to load API stats</div>
            )}
          </Section>

          {/* Engagement History */}
          <Section title={`Engagement History (${engagements.length})`}>
            {engagements.length === 0 ? (
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700 text-slate-500">
                No engagements yet. Browse or view episodes to build your profile.
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {[...engagements].reverse().map((eng, idx) => (
                  <div
                    key={`${eng.episode?.id}-${idx}`}
                    className="bg-slate-800 rounded-lg p-3 border border-slate-700"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${eng.type === 'bookmark'
                          ? 'bg-purple-500/20 text-purple-400'
                          : 'bg-blue-500/20 text-blue-400'
                        }`}>
                        {eng.type}
                      </span>
                      <span className="text-xs text-slate-500">
                        {new Date(eng.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-sm text-white line-clamp-1">{eng.episode?.title}</p>
                    <p className="text-xs text-slate-500">{eng.episode?.series?.name}</p>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* Inferred Interests */}
          <Section title="Inferred Category Interests">
            {sortedCategories.length === 0 ? (
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700 text-slate-500">
                No interests inferred yet.
              </div>
            ) : (
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <div className="space-y-2">
                  {sortedCategories.map(([category, score]) => (
                    <div key={category} className="flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white truncate">{category}</div>
                        <div className="h-2 bg-slate-700 rounded-full mt-1 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${score > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                            style={{ width: `${Math.min(Math.abs(score) * 20, 100)}%` }}
                          />
                        </div>
                      </div>
                      <span className={`text-sm font-mono w-8 text-right ${score > 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                        {score > 0 ? '+' : ''}{score}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>

          {/* Series Activity */}
          {Object.keys(seriesInterests).length > 0 && (
            <Section title="Series Activity">
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <div className="space-y-2">
                  {Object.entries(seriesInterests)
                    .sort((a, b) => b[1].count - a[1].count)
                    .map(([id, data]) => (
                      <div key={id} className="flex items-center justify-between text-sm">
                        <span className="text-white truncate">{data.name}</span>
                        <span className="text-slate-400 ml-2">{data.count} episodes</span>
                      </div>
                    ))}
                </div>
              </div>
            </Section>
          )}

          {/* Not Interested */}
          {notInterested.length > 0 && (
            <Section title={`Not Interested (${notInterested.length})`}>
              <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {notInterested.map((ep, idx) => (
                    <div key={`${ep.id}-${idx}`} className="text-sm text-slate-400 truncate">
                      {ep.title}
                    </div>
                  ))}
                </div>
              </div>
            </Section>
          )}
        </>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold text-white mb-3">{title}</h2>
      {children}
    </div>
  );
}

function StatCard({ label, value, color }) {
  const colorClasses = {
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    indigo: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400',
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
    red: 'bg-red-500/10 border-red-500/30 text-red-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
  };

  return (
    <div className={`rounded-xl p-4 border ${colorClasses[color] || colorClasses.blue}`}>
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
