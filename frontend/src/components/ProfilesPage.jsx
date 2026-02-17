/**
 * Profiles Page - View evaluation profiles with full observability
 * 
 * Displays all profiles used in evaluation tests with complete data visibility.
 */

import { useState, useEffect } from 'react';
import { listProfiles, getProfile } from '../api';

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [profileDetail, setProfileDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  
  // Load profiles list on mount
  useEffect(() => {
    setLoading(true);
    listProfiles()
      .then(data => {
        setProfiles(data.profiles || []);
        setError(null);
      })
      .catch(err => {
        console.error('Failed to load profiles:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);
  
  // Load profile detail when selected
  const handleSelectProfile = async (profileId) => {
    setSelectedProfile(profileId);
    setLoadingDetail(true);
    try {
      const detail = await getProfile(profileId);
      setProfileDetail(detail);
    } catch (err) {
      console.error('Failed to load profile detail:', err);
      setProfileDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };
  
  const handleBackToList = () => {
    setSelectedProfile(null);
    setProfileDetail(null);
  };
  
  if (loading) {
    return (
      <div className="text-center py-12 text-slate-400">
        Loading profiles...
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
        Error loading profiles: {error}
      </div>
    );
  }
  
  // Detail view
  if (selectedProfile && profileDetail) {
    return (
      <div>
        <button
          onClick={handleBackToList}
          className="mb-4 px-3 py-1.5 text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
        >
          ← Back to Profiles
        </button>
        <ProfileDetailView profile={profileDetail} loading={loadingDetail} />
      </div>
    );
  }
  
  // List view
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white">Evaluation Profiles</h2>
        <p className="text-sm text-slate-400">
          {profiles.length} profile{profiles.length !== 1 ? 's' : ''} available
        </p>
      </div>
      
      <div className="space-y-3">
        {profiles.map(profile => (
          <ProfileCard 
            key={profile.id} 
            profile={profile} 
            onClick={() => handleSelectProfile(profile.id)}
          />
        ))}
      </div>
      
      {profiles.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          No profiles found
        </div>
      )}
    </div>
  );
}

function ProfileCard({ profile, onClick }) {
  return (
    <div 
      onClick={onClick}
      className="p-4 bg-slate-800 border border-slate-700 rounded-lg hover:border-indigo-500/50 cursor-pointer transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-white font-medium mb-1">{profile.name}</h3>
          <p className="text-sm text-slate-400 line-clamp-2">{profile.description}</p>
        </div>
        <span className="text-slate-500 text-xs ml-4">→</span>
      </div>
    </div>
  );
}

function ProfileDetailView({ profile, loading }) {
  if (loading) {
    return (
      <div className="text-center py-8 text-slate-400">
        Loading profile details...
      </div>
    );
  }
  
  if (!profile) {
    return (
      <div className="text-center py-8 text-slate-500">
        Failed to load profile
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* Header Card */}
      <div className="p-4 bg-slate-800 border border-slate-700 rounded-lg">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">{profile.name}</h2>
            <p className="text-sm text-slate-500">{profile.profile_id}</p>
          </div>
          <span className="px-3 py-1 bg-indigo-500/20 text-indigo-400 text-xs font-medium rounded">
            {profile.icp_segment || 'Profile'}
          </span>
        </div>
        <p className="text-sm text-slate-300">{profile.description}</p>
      </div>
      
      {/* Metadata Grid */}
      <div className="grid grid-cols-2 gap-4">
        {profile.usage_duration && (
          <MetadataCard label="Usage Duration" value={profile.usage_duration} />
        )}
        {profile.created_at && (
          <MetadataCard 
            label="Created" 
            value={new Date(profile.created_at).toLocaleDateString()} 
          />
        )}
      </div>
      
      {/* Stats Card */}
      {profile.stats && (
        <div className="p-4 bg-slate-800 border border-slate-700 rounded-lg">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">Engagement Statistics</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <StatItem label="Total Engagements" value={profile.stats.total_engagements} />
            <StatItem label="Clicks" value={profile.stats.clicks} />
            <StatItem label="Bookmarks" value={profile.stats.bookmarks} />
            <StatItem label="Effective Weight" value={profile.stats.effective_weight} />
            <StatItem 
              label="Avg Credibility" 
              value={profile.stats.avg_credibility?.toFixed(1) || 'N/A'} 
            />
            <StatItem 
              label="Avg Insight" 
              value={profile.stats.avg_insight?.toFixed(1) || 'N/A'} 
            />
          </div>
        </div>
      )}
      
      {/* Expected Behavior */}
      {profile.expected_behavior && profile.expected_behavior.length > 0 && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <h3 className="text-sm font-semibold text-blue-400 mb-2">Expected Behavior</h3>
          <ul className="space-y-1">
            {profile.expected_behavior.map((behavior, idx) => (
              <li key={idx} className="text-sm text-blue-300 flex items-start gap-2">
                <span className="text-blue-400 mt-0.5">•</span>
                <span>{behavior}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Engagements List */}
      {profile.engagements && profile.engagements.length > 0 && (
        <div className="p-4 bg-slate-800 border border-slate-700 rounded-lg">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">
            Engagement History ({profile.engagements.length})
          </h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {profile.engagements.map((eng, idx) => (
              <EngagementItem key={idx} engagement={eng} />
            ))}
          </div>
        </div>
      )}
      
      {/* Excluded IDs */}
      {profile.excluded_ids && profile.excluded_ids.length > 0 && (
        <div className="p-4 bg-slate-800 border border-slate-700 rounded-lg">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">
            Excluded Episodes ({profile.excluded_ids.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {profile.excluded_ids.map(id => (
              <span 
                key={id} 
                className="px-2 py-1 bg-slate-700 text-slate-400 text-xs font-mono rounded"
              >
                {id}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* Notes */}
      {profile.notes && (
        <div className="p-3 bg-slate-700/30 rounded-lg text-sm text-slate-400 italic">
          {profile.notes}
        </div>
      )}
    </div>
  );
}

function MetadataCard({ label, value }) {
  return (
    <div className="p-3 bg-slate-800 border border-slate-700 rounded-lg">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className="text-sm text-white font-medium">{value}</div>
    </div>
  );
}

function StatItem({ label, value }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold text-white">{value}</div>
    </div>
  );
}

function EngagementItem({ engagement }) {
  const getTypeBadge = (type) => {
    if (type === 'bookmark') {
      return <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded">Bookmark</span>;
    }
    return <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded">Click</span>;
  };
  
  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };
  
  return (
    <div className="p-3 bg-slate-850 rounded-lg">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm text-white font-medium truncate">{engagement.title}</h4>
          <p className="text-xs text-slate-500">{engagement.series}</p>
        </div>
        {getTypeBadge(engagement.type)}
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span className="font-mono">{engagement.episode_id}</span>
        <span>{formatDate(engagement.timestamp)}</span>
      </div>
    </div>
  );
}
