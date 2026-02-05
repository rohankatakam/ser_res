/**
 * Browse Page - Full Catalog View
 * 
 * Simple catalog browser sorted by popularity/quality.
 * Light, clean view for exploring all episodes.
 */

import { useState, useEffect, useMemo } from 'react';

const API_BASE = 'http://localhost:8000';

export default function BrowsePage({ onView, onBookmark, excludedIds }) {
  const [episodes, setEpisodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('quality'); // 'quality', 'recent', 'credibility'
  const [filterCategory, setFilterCategory] = useState('all');
  
  // Load episodes
  useEffect(() => {
    async function loadEpisodes() {
      try {
        const res = await fetch(`${API_BASE}/api/episodes`);
        if (!res.ok) throw new Error('API error');
        const data = await res.json();
        setEpisodes(data.episodes || []);
      } catch (err) {
        setError('API not running. Start with: cd mock_api && python server.py');
      } finally {
        setLoading(false);
      }
    }
    loadEpisodes();
  }, []);
  
  // Get unique categories
  const categories = useMemo(() => {
    const cats = new Set();
    episodes.forEach(ep => {
      (ep.categories?.major || []).forEach(c => cats.add(c));
    });
    return ['all', ...Array.from(cats).sort()];
  }, [episodes]);
  
  // Sort and filter episodes
  const displayEpisodes = useMemo(() => {
    let filtered = episodes.filter(ep => {
      if (filterCategory !== 'all') {
        return ep.categories?.major?.includes(filterCategory);
      }
      return true;
    });
    
    return filtered.sort((a, b) => {
      const aScores = a.scores || {};
      const bScores = b.scores || {};
      
      switch (sortBy) {
        case 'quality':
          const aQuality = (aScores.credibility || 0) + (aScores.insight || 0);
          const bQuality = (bScores.credibility || 0) + (bScores.insight || 0);
          return bQuality - aQuality;
        case 'recent':
          return new Date(b.published_at) - new Date(a.published_at);
        case 'credibility':
          return (bScores.credibility || 0) - (aScores.credibility || 0);
        default:
          return 0;
      }
    });
  }, [episodes, sortBy, filterCategory]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-pulse text-slate-400">Loading catalog...</div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-96 p-4">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <code className="bg-slate-800 px-3 py-2 rounded text-green-400 text-sm">
            cd rec/mock_api && python server.py
          </code>
        </div>
      </div>
    );
  }
  
  return (
    <div className="p-4 pb-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-1">Browse Catalog</h1>
        <p className="text-slate-400 text-sm">{episodes.length} episodes available</p>
      </div>
      
      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="bg-slate-800 text-white text-sm rounded-lg px-3 py-2 border border-slate-700 focus:border-indigo-500 outline-none"
        >
          <option value="quality">Sort by Quality (C+I)</option>
          <option value="recent">Sort by Recent</option>
          <option value="credibility">Sort by Credibility</option>
        </select>
        
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="bg-slate-800 text-white text-sm rounded-lg px-3 py-2 border border-slate-700 focus:border-indigo-500 outline-none"
        >
          {categories.map(cat => (
            <option key={cat} value={cat}>
              {cat === 'all' ? 'All Categories' : cat}
            </option>
          ))}
        </select>
        
        <div className="ml-auto text-sm text-slate-500">
          Showing {displayEpisodes.length} episodes
        </div>
      </div>
      
      {/* Episode Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {displayEpisodes.map(episode => (
          <EpisodeCard
            key={episode.id}
            episode={episode}
            isViewed={excludedIds.has(episode.id)}
            onView={onView}
            onBookmark={onBookmark}
          />
        ))}
      </div>
    </div>
  );
}

function EpisodeCard({ episode, isViewed, onView, onBookmark }) {
  const { title, series, published_at, scores, key_insight, categories } = episode;
  
  const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };
  
  const qualityScore = (scores?.credibility || 0) + (scores?.insight || 0);
  
  return (
    <div 
      className={`bg-slate-800 rounded-xl border overflow-hidden transition-colors cursor-pointer ${
        isViewed 
          ? 'border-slate-600 opacity-60' 
          : 'border-slate-700 hover:border-indigo-500/50'
      }`}
      onClick={() => onView?.(episode)}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex gap-3 mb-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold flex-shrink-0 text-sm">
            {series?.name?.charAt(0) || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-white line-clamp-2 leading-tight">
              {title}
            </h3>
            <p className="text-xs text-slate-400 truncate">{series?.name}</p>
          </div>
        </div>
        
        {/* Scores Row */}
        <div className="flex items-center gap-3 mb-2 text-xs">
          <span className="px-2 py-0.5 bg-slate-700 rounded text-slate-300">
            C:{scores?.credibility || 0} I:{scores?.insight || 0}
          </span>
          <span className={`px-2 py-0.5 rounded ${
            qualityScore >= 6 ? 'bg-green-500/20 text-green-400' :
            qualityScore >= 5 ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-slate-700 text-slate-400'
          }`}>
            Quality: {qualityScore}
          </span>
          <span className="text-slate-500 ml-auto">{formatDate(published_at)}</span>
        </div>
        
        {/* Categories */}
        {categories?.major?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {categories.major.slice(0, 2).map(cat => (
              <span key={cat} className="text-xs px-2 py-0.5 bg-slate-700 rounded text-slate-400">
                {cat}
              </span>
            ))}
          </div>
        )}
        
        {/* Key insight preview */}
        {key_insight && (
          <p className="text-xs text-slate-500 line-clamp-2">"{key_insight}"</p>
        )}
        
        {isViewed && (
          <div className="mt-2 text-xs text-indigo-400">Already viewed</div>
        )}
      </div>
    </div>
  );
}
