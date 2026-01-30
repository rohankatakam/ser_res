/**
 * Episode card component - clickable with signals
 */

import Badge from './Badge';

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function EpisodeCard({ episode, onEpisodeClick, onNotInterested, onSave }) {
  const { title, series, published_at, scores, badges, key_insight, categories } = episode;
  
  // Get primary category
  const primaryCategory = categories?.major?.[0] || null;
  
  // Determine badges from scores if not provided
  const displayBadges = badges || [];
  if (displayBadges.length === 0) {
    if (scores?.insight >= 3) displayBadges.push('high_insight');
    if (scores?.credibility >= 3) displayBadges.push('high_credibility');
    if (episode.critical_views?.has_critical_views) displayBadges.push('contrarian');
  }
  
  const handleCardClick = () => {
    onEpisodeClick?.(episode);
  };
  
  const handleNotInterested = (e) => {
    e.stopPropagation();
    onNotInterested?.(episode);
  };
  
  const handleSave = (e) => {
    e.stopPropagation();
    onSave?.(episode);
  };
  
  return (
    <div 
      onClick={handleCardClick}
      className="flex-shrink-0 w-72 bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-indigo-500 hover:bg-slate-750 transition-all cursor-pointer group"
    >
      {/* Click indicator */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-xs text-indigo-400">Click to signal interest →</span>
      </div>
      
      {/* Header */}
      <div className="flex gap-3 mb-3">
        {/* Podcast artwork placeholder */}
        <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-xl font-bold flex-shrink-0">
          {series?.name?.charAt(0) || '?'}
        </div>
        
        <div className="flex-1 min-w-0">
          {/* Episode title */}
          <h3 className="text-sm font-semibold text-white line-clamp-2 leading-tight mb-1">
            {title}
          </h3>
          
          {/* Series name */}
          <p className="text-xs text-slate-400 truncate">
            {series?.name}
          </p>
          
          {/* Date */}
          <p className="text-xs text-slate-500 mt-0.5">
            {formatDate(published_at)}
          </p>
        </div>
      </div>
      
      {/* Scores display */}
      {scores && (
        <div className="flex gap-2 mb-2 text-xs">
          <span className="text-purple-400" title="Insight">💎 {scores.insight || 0}</span>
          <span className="text-yellow-400" title="Credibility">⭐ {scores.credibility || 0}</span>
          <span className="text-blue-400" title="Information">📊 {scores.information || 0}</span>
        </div>
      )}
      
      {/* Badges */}
      {displayBadges.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {displayBadges.slice(0, 2).map((badge) => (
            <Badge key={badge} type={badge} />
          ))}
        </div>
      )}
      
      {/* Key insight preview */}
      {key_insight && (
        <p className="text-xs text-slate-300 line-clamp-3 mb-3 leading-relaxed">
          "{key_insight}"
        </p>
      )}
      
      {/* Category tag */}
      {primaryCategory && (
        <div className="mb-3">
          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs bg-slate-700 text-slate-300">
            🏷️ {primaryCategory}
          </span>
        </div>
      )}
      
      {/* Actions */}
      <div className="flex justify-between items-center pt-2 border-t border-slate-700">
        <button 
          onClick={handleSave}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-purple-400 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
          Save
        </button>
        
        <button 
          onClick={handleNotInterested}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-red-400 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
          Not for me
        </button>
      </div>
    </div>
  );
}
