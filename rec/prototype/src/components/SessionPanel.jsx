/**
 * Session Panel — V1.1 Session Pool (Option C)
 * 
 * Shows current session state for debugging:
 * - Active session ID
 * - Session queue status
 * - Engagement history (clicks, bookmarks)
 * - Inferred preferences
 * - Excluded episodes
 */

function formatTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

function formatDate(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function SessionPanel({ session, inferred, activeSessionId, onReset }) {
  const engagements = session?.engagements || [];
  const notInterested = session?.notInterestedEpisodes || [];
  const categoryInterests = session?.categoryInterests || {};
  const seriesInterests = session?.seriesInterests || {};
  
  // Group engagements by type
  const clicks = engagements.filter(e => e.type === 'click');
  const bookmarks = engagements.filter(e => e.type === 'bookmark');
  
  // Sort categories by score
  const sortedCategories = Object.entries(categoryInterests)
    .sort((a, b) => b[1] - a[1]);
  
  return (
    <div className="fixed right-0 top-16 bottom-0 w-80 bg-slate-800 border-l border-slate-700 overflow-y-auto">
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white">Session State</h2>
          <button
            onClick={onReset}
            className="text-xs text-red-400 hover:text-red-300"
          >
            Reset
          </button>
        </div>
        
        {/* Active Session */}
        {activeSessionId && (
          <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 mb-4">
            <h3 className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-1">
              Active Session
            </h3>
            <p className="text-sm font-mono text-purple-300">{activeSessionId}</p>
            <p className="text-xs text-slate-400 mt-1">
              Queue is deterministic • Load More = next N
            </p>
          </div>
        )}
        
        {/* Summary */}
        <div className="bg-slate-900 rounded-lg p-3 mb-4">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-slate-500">Engagements:</span>
              <span className="text-white ml-2">{engagements.length}</span>
            </div>
            <div>
              <span className="text-slate-500">Excluded:</span>
              <span className="text-red-400 ml-2">{inferred?.totalExcluded || 0}</span>
            </div>
            <div>
              <span className="text-slate-500">Clicks:</span>
              <span className="text-blue-400 ml-2">{clicks.length}</span>
            </div>
            <div>
              <span className="text-slate-500">Bookmarks:</span>
              <span className="text-purple-400 ml-2">{bookmarks.length}</span>
            </div>
          </div>
        </div>
        
        {/* Algorithm Info */}
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg p-3 mb-4">
          <h3 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
            V1.1 Session Pool
          </h3>
          <p className="text-xs text-slate-300">
            {engagements.length === 0 ? (
              <>Cold start: Quality-ranked queue (C+I score)</>
            ) : engagements.length < 2 ? (
              <>Building vector... ({engagements.length}/2 min)</>
            ) : (
              <>Personalized: Vector from {Math.min(engagements.length, 5)} engagements</>
            )}
          </p>
          <div className="mt-2 pt-2 border-t border-indigo-500/20 text-xs text-slate-400">
            <p>• <strong>Load More</strong> = next 10 from queue</p>
            <p>• <strong>Refresh</strong> = new session with fresh rankings</p>
          </div>
        </div>
        
        {/* Engagement History */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
            <span>📊</span> Engagement History
            {engagements.length > 0 && (
              <span className="text-xs text-slate-500">({engagements.length})</span>
            )}
          </h3>
          
          {engagements.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No engagements yet. Click on episodes to engage.</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {[...engagements].reverse().map((eng, idx) => (
                <div 
                  key={`${eng.episode?.id}-${eng.timestamp}-${idx}`}
                  className="bg-slate-900 rounded p-2 text-xs"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={eng.type === 'bookmark' ? 'text-purple-400' : 'text-blue-400'}>
                      {eng.type === 'bookmark' ? '🔖' : '👆'}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                      eng.type === 'bookmark' 
                        ? 'bg-purple-500/20 text-purple-400' 
                        : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {eng.type} {eng.type === 'bookmark' ? '(2x)' : '(1x)'}
                    </span>
                    <span className="text-slate-500 ml-auto">{formatTime(eng.timestamp)}</span>
                  </div>
                  <p className="text-slate-300 line-clamp-1">
                    {eng.episode?.title || 'Unknown episode'}
                  </p>
                  <p className="text-slate-500 text-[10px]">
                    {eng.episode?.series?.name}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Category Interests */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
            <span>🏷️</span> Inferred Interests
          </h3>
          
          {sortedCategories.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No interests inferred yet.</p>
          ) : (
            <div className="space-y-1">
              {sortedCategories.map(([category, score]) => (
                <div 
                  key={category}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-slate-300 truncate flex-1">{category}</span>
                  <span className={`ml-2 font-mono ${
                    score > 0 ? 'text-green-400' : score < 0 ? 'text-red-400' : 'text-slate-500'
                  }`}>
                    {score > 0 ? '+' : ''}{score}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Series Interests */}
        {Object.keys(seriesInterests).length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <span>🎙️</span> Series Activity
            </h3>
            <div className="space-y-1">
              {Object.entries(seriesInterests)
                .sort((a, b) => b[1].count - a[1].count)
                .slice(0, 5)
                .map(([id, data]) => (
                  <div key={id} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 truncate flex-1">{data.name}</span>
                    <span className="ml-2 text-slate-500">{data.count} eps</span>
                  </div>
                ))}
            </div>
          </div>
        )}
        
        {/* Not Interested */}
        {notInterested.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-2">
              <span>🚫</span> Not Interested ({notInterested.length})
            </h3>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {notInterested.map((ep, idx) => (
                <div key={`${ep.id}-${idx}`} className="text-xs text-slate-500 truncate">
                  {ep.title}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Debug: Embedding Info */}
        <div className="mt-4 pt-4 border-t border-slate-700">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            User Vector Info
          </h3>
          <div className="text-xs text-slate-400 space-y-1">
            <p>Episodes in vector: {Math.min(engagements.length, 5)}</p>
            <p>Vector type: Simple mean (Option A)</p>
            <p>Embedding fields: title + key_insights</p>
          </div>
        </div>
        
        {/* Instructions */}
        <div className="mt-4 pt-4 border-t border-slate-700">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Testing Guide (Option C)
          </h3>
          <div className="text-xs text-slate-400 space-y-2">
            <p><strong>1.</strong> View creates session with ranked queue</p>
            <p><strong>2.</strong> Click episodes to engage (builds vector)</p>
            <p><strong>3.</strong> "Load More" = next 10 (no recompute)</p>
            <p><strong>4.</strong> "Refresh" = new session, fresh rankings</p>
            <p><strong>5.</strong> Reset = clear all, test cold start</p>
          </div>
        </div>
      </div>
    </div>
  );
}
