/**
 * Episode Card - Click to VIEW (marks as seen, excludes from future recs)
 */

function formatDate(dateString) {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function EpisodeCard({ episode, onView, onBookmark, onNotInterested }) {
  const { title, series, published_at, scores, categories, key_insight } = episode;
  
  const primaryCategory = categories?.major?.[0];
  
  return (
    <div className="flex-shrink-0 w-72 bg-slate-800 rounded-xl border border-slate-700 overflow-hidden hover:border-slate-500 transition-colors">
      {/* Clickable content area - VIEW action */}
      <div 
        onClick={() => onView?.(episode)}
        className="p-4 cursor-pointer hover:bg-slate-750"
      >
        {/* Header */}
        <div className="flex gap-3 mb-3">
          <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold flex-shrink-0">
            {series?.name?.charAt(0) || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-white line-clamp-2 leading-tight">
              {title}
            </h3>
            <p className="text-xs text-slate-400 truncate">{series?.name}</p>
            <p className="text-xs text-slate-500">{formatDate(published_at)}</p>
          </div>
        </div>
        
        {/* Scores */}
        {scores && (
          <div className="flex gap-3 mb-2 text-xs">
            <span className="text-purple-400">💎 {scores.insight || 0}</span>
            <span className="text-yellow-400">⭐ {scores.credibility || 0}</span>
            <span className="text-blue-400">📊 {scores.information || 0}</span>
          </div>
        )}
        
        {/* Key insight */}
        {key_insight && (
          <p className="text-xs text-slate-300 line-clamp-2 mb-2">"{key_insight}"</p>
        )}
        
        {/* Category */}
        {primaryCategory && (
          <span className="inline-block px-2 py-0.5 text-xs bg-slate-700 text-slate-300 rounded">
            {primaryCategory}
          </span>
        )}
      </div>
      
      {/* Action buttons */}
      <div className="flex border-t border-slate-700">
        <button
          onClick={(e) => { e.stopPropagation(); onView?.(episode); }}
          className="flex-1 py-2 text-xs text-indigo-400 hover:bg-indigo-500/20 transition-colors"
        >
          ▶ View
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onBookmark?.(episode); }}
          className="flex-1 py-2 text-xs text-purple-400 hover:bg-purple-500/20 border-l border-slate-700 transition-colors"
        >
          🔖 Save
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onNotInterested?.(episode); }}
          className="flex-1 py-2 text-xs text-slate-500 hover:bg-red-500/20 hover:text-red-400 border-l border-slate-700 transition-colors"
        >
          ✕ Hide
        </button>
      </div>
    </div>
  );
}
