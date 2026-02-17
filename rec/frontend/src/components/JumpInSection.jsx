/**
 * Jump In Section - Shows user's recently viewed episodes
 * 
 * This is the HISTORY interface (separate from recommendations).
 * Displayed at the top of the discover page so viewed content doesn't "disappear".
 */

function formatDate(dateString) {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatTimeAgo(timestamp) {
  if (!timestamp) return '';
  const now = new Date();
  const viewed = new Date(timestamp);
  const diffMs = now - viewed;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export default function JumpInSection({ viewedEpisodes, bookmarkedEpisodes }) {
  // Combine and sort by most recent first
  const recentHistory = [
    ...viewedEpisodes.map(item => ({ ...item, type: 'viewed' })),
    ...bookmarkedEpisodes.map(item => ({ ...item, type: 'bookmarked' })),
  ]
    .sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0))
    .slice(0, 10);
  
  if (recentHistory.length === 0) return null;
  
  return (
    <div className="mb-6">
      {/* Section header */}
      <div className="px-4 mb-2">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">⏱️ Jump In</h2>
            <p className="text-sm text-slate-400">Pick up where you left off</p>
          </div>
          <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
            {recentHistory.length} episode{recentHistory.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>
      
      {/* Episodes scroll */}
      <div className="overflow-x-auto hide-scrollbar">
        <div className="flex gap-3 px-4 pb-2">
          {recentHistory.map((item, idx) => {
            const ep = item.episode;
            return (
              <div
                key={`${ep.content_id || ep.id}-${idx}`}
                className="flex-shrink-0 w-56 bg-slate-800/70 rounded-xl border border-slate-700 overflow-hidden hover:border-slate-500 transition-colors"
              >
                <div className="p-3">
                  {/* Header with thumbnail */}
                  <div className="flex gap-2 mb-2">
                    <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                      {ep.series?.name?.charAt(0) || '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-xs font-semibold text-white line-clamp-2 leading-tight">
                        {ep.title}
                      </h3>
                      <p className="text-xs text-slate-500 truncate">{ep.series?.name}</p>
                    </div>
                  </div>
                  
                  {/* Status row */}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">
                      {formatTimeAgo(item.timestamp)}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded ${
                      item.type === 'bookmarked' 
                        ? 'bg-purple-500/20 text-purple-400' 
                        : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {item.type === 'bookmarked' ? '🔖 Saved' : '▶ Viewed'}
                    </span>
                  </div>
                  
                  {/* Progress bar (placeholder for future) */}
                  {item.progress !== undefined && (
                    <div className="mt-2">
                      <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-indigo-500 rounded-full"
                          style={{ width: `${Math.round(item.progress * 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {Math.round(item.progress * 100)}% complete
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
