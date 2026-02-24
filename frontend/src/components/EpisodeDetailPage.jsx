/**
 * Episode Detail Page
 * 
 * Shows full episode details including:
 * - Title, series, published date
 * - All scores (credibility, insight, information, entertainment)
 * - Key insights
 * - Entities mentioned with context
 * - Categories
 * - POV status (contrarian/consensus)
 */

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    weekday: 'long',
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
}

function formatDaysAgo(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const days = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

function ScoreCard({ label, score, icon, color }) {
  const getScoreLabel = (s) => {
    if (s >= 4) return 'Exceptional';
    if (s >= 3) return 'Strong';
    if (s >= 2) return 'Adequate';
    return 'Weak';
  };
  
  const getBarWidth = (s) => `${(s / 4) * 100}%`;
  
  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-400 text-sm flex items-center gap-2">
          <span>{icon}</span>
          {label}
        </span>
        <span className={`text-xl font-bold ${color}`}>{score}/4</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color.replace('text-', 'bg-')} rounded-full transition-all`}
          style={{ width: getBarWidth(score) }}
        />
      </div>
      <p className="text-xs text-slate-500 mt-1">{getScoreLabel(score)}</p>
    </div>
  );
}

function EntityCard({ entity }) {
  const getRelevanceLabel = (r) => {
    if (r >= 4) return 'Primary Focus';
    if (r >= 3) return 'Major Topic';
    if (r >= 2) return 'Discussed';
    return 'Mentioned';
  };
  
  return (
    <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-white">{entity.name}</h4>
        <span className="text-xs px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded">
          Relevance: {entity.relevance}/4
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-2">{getRelevanceLabel(entity.relevance)}</p>
      {entity.context && (
        <p className="text-sm text-slate-300">{entity.context}</p>
      )}
    </div>
  );
}

export default function EpisodeDetailPage({ episode, onBack, onBookmark }) {
  if (!episode) {
    return (
      <div className="p-8 text-center text-slate-400">
        <p>Episode not found</p>
        <button onClick={onBack} className="mt-4 text-indigo-400 hover:underline">
          ← Back to feed
        </button>
      </div>
    );
  }
  
  const { 
    title, 
    series, 
    published_at, 
    scores, 
    categories, 
    entities,
    people,
    key_insight,
  } = episode;
  
  // Determine quality status based on scores
  const getQualityStatus = () => {
    const c = scores?.credibility || 0;
    const i = scores?.insight || 0;
    if (c >= 3 && i >= 3) {
      return { label: 'High Quality', color: 'text-purple-400', bg: 'bg-purple-500/20' };
    }
    if (c >= 3) {
      return { label: 'High Credibility', color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
    }
    if (i >= 3) {
      return { label: 'High Insight', color: 'text-indigo-400', bg: 'bg-indigo-500/20' };
    }
    return { label: 'Standard', color: 'text-slate-400', bg: 'bg-slate-700' };
  };
  
  const qualityBadge = getQualityStatus();
  
  // Get key insights text
  const keyInsightsText = key_insight || null;
  
  return (
    <div className="max-w-4xl mx-auto pb-12">
      {/* Back button */}
      <div className="sticky top-0 z-10 bg-slate-900 border-b border-slate-700 px-4 py-3">
        <button 
          onClick={onBack}
          className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
        >
          <span>←</span>
          <span>Back to feed</span>
        </button>
      </div>
      
      {/* Header */}
      <div className="p-6 border-b border-slate-700">
        <div className="flex gap-4 mb-4">
          <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white text-2xl font-bold flex-shrink-0">
            {series?.name?.charAt(0) || '?'}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-white mb-2 leading-tight">
              {title}
            </h1>
            <p className="text-indigo-400 font-medium">{series?.name}</p>
            <div className="flex items-center gap-3 mt-2 text-sm text-slate-400">
              <span>{formatDate(published_at)}</span>
              <span className="text-slate-600">•</span>
              <span>{formatDaysAgo(published_at)}</span>
            </div>
          </div>
        </div>
        
        {/* Quality Badge and Action Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${qualityBadge.bg} ${qualityBadge.color}`}>
              {qualityBadge.label}
            </span>
          </div>
          <button
            onClick={() => onBookmark?.(episode)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            🔖 Bookmark
          </button>
        </div>
      </div>
      
      {/* Scores Grid */}
      <div className="p-6 border-b border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">Quality Scores</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <ScoreCard 
            label="Credibility" 
            score={scores?.credibility || 0} 
            icon="⭐" 
            color="text-yellow-400" 
          />
          <ScoreCard 
            label="Insight" 
            score={scores?.insight || 0} 
            icon="💎" 
            color="text-purple-400" 
          />
          <ScoreCard 
            label="Information" 
            score={scores?.information || 0} 
            icon="📊" 
            color="text-blue-400" 
          />
          <ScoreCard 
            label="Entertainment" 
            score={scores?.entertainment || 0} 
            icon="🎬" 
            color="text-pink-400" 
          />
        </div>
        
        {/* Combined Score */}
        <div className="mt-4 p-4 bg-slate-800 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Combined (C + I):</span>
            <span className={`text-xl font-bold ${(scores?.credibility + scores?.insight) >= 5 ? 'text-green-400' : 'text-red-400'}`}>
              {(scores?.credibility || 0) + (scores?.insight || 0)}/8
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {(scores?.credibility + scores?.insight) >= 5 
              ? '✓ Passes quality threshold (C+I ≥ 5)' 
              : '✗ Below quality threshold (needs C+I ≥ 5)'
            }
          </p>
        </div>
      </div>
      
      {/* Key Insights */}
      {keyInsightsText && (
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Key Insights</h2>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <p className="text-slate-200 whitespace-pre-wrap leading-relaxed">
              {keyInsightsText}
            </p>
          </div>
        </div>
      )}
      
      {/* Categories */}
      <div className="p-6 border-b border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">Categories</h2>
        <div className="flex flex-wrap gap-2">
          {categories?.major?.map(cat => (
            <span 
              key={cat}
              className="px-3 py-1.5 bg-indigo-500/20 text-indigo-300 rounded-lg text-sm"
            >
              {cat}
            </span>
          ))}
          {categories?.subcategories?.map(cat => (
            <span 
              key={cat}
              className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg text-sm"
            >
              {cat}
            </span>
          ))}
        </div>
      </div>
      
      {/* Entities */}
      {entities && entities.length > 0 && (
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">
            Entities Mentioned ({entities.length})
          </h2>
          <div className="space-y-3">
            {entities.map((entity, idx) => (
              <EntityCard key={`${entity.name}-${idx}`} entity={entity} />
            ))}
          </div>
        </div>
      )}
      
      {/* People */}
      {people && people.length > 0 && (
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">
            People ({people.length})
          </h2>
          <div className="space-y-3">
            {people.map((person, idx) => (
              <div key={idx} className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-white">{person.name}</h4>
                  {person.relevance && (
                    <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded">
                      Relevance: {person.relevance}/4
                    </span>
                  )}
                </div>
                {person.title && (
                  <p className="text-sm text-slate-400 mb-1">{person.title}</p>
                )}
                {person.context && (
                  <p className="text-sm text-slate-300">{person.context}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Debug Info */}
      <div className="p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Episode Metadata</h2>
        <div className="bg-slate-800 rounded-lg p-4 font-mono text-xs text-slate-400 overflow-x-auto">
          <p><span className="text-slate-500">ID:</span> {episode.id}</p>
          <p><span className="text-slate-500">Content ID:</span> {episode.content_id}</p>
          <p><span className="text-slate-500">Series ID:</span> {series?.id}</p>
          <p><span className="text-slate-500">Quality:</span> {qualityBadge.label}</p>
        </div>
      </div>
    </div>
  );
}
