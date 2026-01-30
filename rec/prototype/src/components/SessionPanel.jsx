/**
 * Session Panel - Shows transparent algorithm state
 */

export default function SessionPanel({ session, inferred, onReset }) {
  return (
    <div className="fixed right-0 top-14 bottom-0 w-80 bg-slate-800 border-l border-slate-700 overflow-y-auto">
      <div className="p-4">
        <h2 className="text-lg font-bold text-white mb-4">Session State</h2>
        
        {/* Cold Start Indicator */}
        {session.clicks.length === 0 && (
          <div className="mb-4 p-3 bg-blue-500/20 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-300 font-medium">🥶 Cold Start Active</p>
            <p className="text-xs text-blue-400 mt-1">
              Showing global quality content. Click episodes to personalize.
            </p>
          </div>
        )}
        
        {/* Inferred Categories */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">Inferred Interests</h3>
          {inferred.topCategories.length > 0 ? (
            <div className="space-y-1">
              {inferred.topCategories.map(([cat, score]) => (
                <div key={cat} className="flex items-center justify-between">
                  <span className="text-sm text-white">{cat}</span>
                  <span className="text-xs text-green-400">+{score}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">No preferences yet</p>
          )}
        </div>
        
        {/* Excluded Categories */}
        {inferred.excludedCategories.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">Deprioritized</h3>
            <div className="space-y-1">
              {inferred.excludedCategories.map(cat => (
                <div key={cat} className="flex items-center justify-between">
                  <span className="text-sm text-slate-400 line-through">{cat}</span>
                  <span className="text-xs text-red-400">excluded</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Implicit Subscriptions */}
        {inferred.implicitSubscriptions.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">
              Implicit Subscriptions (2+ clicks)
            </h3>
            <div className="space-y-1">
              {inferred.implicitSubscriptions.map(series => (
                <div key={series.id} className="flex items-center justify-between">
                  <span className="text-sm text-white truncate">{series.name}</span>
                  <span className="text-xs text-purple-400">{series.count}x</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Quality Preference */}
        {inferred.avgInsightClicked && (
          <div className="mb-4">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">Quality Preference</h3>
            <p className="text-sm text-white">
              Avg Insight Score Clicked: <span className="text-yellow-400">{inferred.avgInsightClicked}</span>
            </p>
          </div>
        )}
        
        <hr className="border-slate-700 my-4" />
        
        {/* Recent Clicks */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">
            Recent Clicks ({session.clicks.length})
          </h3>
          {session.clicks.length > 0 ? (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {session.clicks.slice(-5).reverse().map((ep, i) => (
                <div key={i} className="text-xs text-slate-300 p-2 bg-slate-700/50 rounded">
                  <p className="truncate font-medium">{ep.title}</p>
                  <p className="text-slate-500">{ep.series?.name}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">No clicks yet</p>
          )}
        </div>
        
        {/* Not Interested */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">
            Not Interested ({session.notInterested.length})
          </h3>
          {session.notInterested.length > 0 ? (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {session.notInterested.slice(-5).reverse().map((ep, i) => (
                <div key={i} className="text-xs text-red-300/70 p-2 bg-red-900/20 rounded">
                  <p className="truncate">{ep.title}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">None excluded</p>
          )}
        </div>
        
        {/* Saves */}
        <div className="mb-4">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">
            Saved ({session.saves.length})
          </h3>
          {session.saves.length > 0 ? (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {session.saves.slice(-5).reverse().map((ep, i) => (
                <div key={i} className="text-xs text-purple-300 p-2 bg-purple-900/20 rounded">
                  <p className="truncate">{ep.title}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">None saved</p>
          )}
        </div>
        
        <hr className="border-slate-700 my-4" />
        
        {/* Export */}
        <button
          onClick={() => {
            const data = JSON.stringify({ session, inferred }, null, 2);
            console.log('Session Export:', data);
            navigator.clipboard?.writeText(data);
            alert('Session data copied to clipboard!');
          }}
          className="w-full px-3 py-2 text-sm bg-slate-700 text-slate-300 rounded hover:bg-slate-600 mb-2"
        >
          Export Session State
        </button>
        
        <button
          onClick={onReset}
          className="w-full px-3 py-2 text-sm bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
        >
          Reset to Cold Start
        </button>
      </div>
    </div>
  );
}
