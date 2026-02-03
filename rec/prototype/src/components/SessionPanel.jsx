/**
 * Session Panel - Shows user activity state
 */

export default function SessionPanel({ session, inferred, onReset }) {
  return (
    <div className="fixed right-0 top-14 bottom-0 w-80 bg-slate-800 border-l border-slate-700 overflow-y-auto">
      <div className="p-4">
        <h2 className="text-lg font-bold text-white mb-4">User State</h2>
        
        {/* Summary */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="p-2 bg-slate-700/50 rounded text-center">
            <div className="text-lg font-bold text-blue-400">{session.viewedEpisodes.length}</div>
            <div className="text-xs text-slate-500">Viewed</div>
          </div>
          <div className="p-2 bg-slate-700/50 rounded text-center">
            <div className="text-lg font-bold text-purple-400">{session.bookmarkedEpisodes.length}</div>
            <div className="text-xs text-slate-500">Saved</div>
          </div>
          <div className="p-2 bg-slate-700/50 rounded text-center">
            <div className="text-lg font-bold text-red-400">{session.notInterestedEpisodes.length}</div>
            <div className="text-xs text-slate-500">Hidden</div>
          </div>
        </div>
        
        <hr className="border-slate-700 my-4" />
        
        {/* Inferred Interests */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">Category Interests</h3>
          {inferred.topCategories.length > 0 ? (
            <div className="space-y-1">
              {inferred.topCategories.map(([cat, score]) => (
                <div key={cat} className="flex justify-between text-sm">
                  <span className="text-white truncate">{cat}</span>
                  <span className="text-green-400">+{score}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">None yet - view some episodes</p>
          )}
          
          {inferred.excludedCategories.length > 0 && (
            <div className="mt-2 pt-2 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-1">Deprioritized:</p>
              {inferred.excludedCategories.map(cat => (
                <div key={cat} className="text-sm text-red-400 line-through">{cat}</div>
              ))}
            </div>
          )}
        </div>
        
        {/* Implicit Subscriptions */}
        {inferred.implicitSubscriptions.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">
              Implicit Subscriptions
            </h3>
            <div className="space-y-1">
              {inferred.implicitSubscriptions.map(s => (
                <div key={s.id} className="flex justify-between text-sm">
                  <span className="text-white truncate">{s.name}</span>
                  <span className="text-purple-400">{s.count}x viewed</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <hr className="border-slate-700 my-4" />
        
        {/* Recent Activity */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">
            Recently Viewed ({session.viewedEpisodes.length})
          </h3>
          {session.viewedEpisodes.length > 0 ? (
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {session.viewedEpisodes.slice(-5).reverse().map((item, i) => {
                const ep = item.episode || item;
                return (
                  <div key={i} className="text-xs p-2 bg-slate-700/30 rounded">
                    <p className="text-slate-300 truncate">{ep.title}</p>
                    <p className="text-slate-500">{ep.series?.name}</p>
                    {item.timestamp && (
                      <p className="text-slate-600 text-[10px]">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">None yet</p>
          )}
        </div>
        
        {/* Hidden */}
        {session.notInterestedEpisodes.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">
              Hidden ({session.notInterestedEpisodes.length})
            </h3>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {session.notInterestedEpisodes.slice(-3).reverse().map((ep, i) => (
                <div key={i} className="text-xs p-2 bg-red-900/20 rounded text-red-300/70 truncate">
                  {ep.title}
                </div>
              ))}
            </div>
          </div>
        )}
        
        <hr className="border-slate-700 my-4" />
        
        {/* Actions */}
        <button
          onClick={() => {
            const data = { session, inferred };
            console.log('Session:', data);
            navigator.clipboard?.writeText(JSON.stringify(data, null, 2));
            alert('Session exported to clipboard!');
          }}
          className="w-full mb-2 px-3 py-2 text-sm bg-slate-700 text-slate-300 rounded hover:bg-slate-600"
        >
          Export Session
        </button>
        
        <button
          onClick={onReset}
          className="w-full px-3 py-2 text-sm bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
        >
          Reset All
        </button>
      </div>
    </div>
  );
}
