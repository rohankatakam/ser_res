/**
 * Recommendation Section - Horizontal scroll with "why" explanation
 */

import { useState } from 'react';
import EpisodeCard from './EpisodeCard';

export default function RecommendationSection({ section, onView, onBookmark, onNotInterested }) {
  const [showWhy, setShowWhy] = useState(false);
  const { title, subtitle, why, episodes } = section;
  
  if (!episodes || episodes.length === 0) return null;
  
  return (
    <div className="mb-6">
      {/* Section header */}
      <div className="px-4 mb-2">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">{title}</h2>
            {subtitle && <p className="text-sm text-slate-400">{subtitle}</p>}
          </div>
          <button
            onClick={() => setShowWhy(!showWhy)}
            className="text-xs text-slate-500 hover:text-slate-300 px-2 py-1 rounded bg-slate-800"
          >
            {showWhy ? 'Hide' : 'Why?'}
          </button>
        </div>
        
        {showWhy && (
          <div className="mt-2 p-2 bg-slate-800/50 border border-slate-700 rounded text-xs text-slate-400">
            <strong className="text-slate-300">Algorithm:</strong> {why}
          </div>
        )}
      </div>
      
      {/* Episodes scroll */}
      <div className="overflow-x-auto hide-scrollbar">
        <div className="flex gap-3 px-4 pb-2">
          {episodes.map((ep) => (
            <EpisodeCard
              key={ep.content_id || ep.id}
              episode={ep}
              onView={onView}
              onBookmark={onBookmark}
              onNotInterested={onNotInterested}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
