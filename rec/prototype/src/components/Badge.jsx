/**
 * Quality badge component for episodes
 */

const badgeConfig = {
  highly_contrarian: {
    label: '🔥 Highly Contrarian',
    className: 'bg-orange-500/20 text-orange-300 border-orange-500/30'
  },
  contrarian: {
    label: '🔥 Contrarian',
    className: 'bg-orange-500/20 text-orange-300 border-orange-500/30'
  },
  high_insight: {
    label: '💎 High Insight',
    className: 'bg-purple-500/20 text-purple-300 border-purple-500/30'
  },
  high_credibility: {
    label: '⭐ High Credibility',
    className: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
  },
  data_rich: {
    label: '📊 Data-Rich',
    className: 'bg-blue-500/20 text-blue-300 border-blue-500/30'
  }
};

export default function Badge({ type }) {
  const config = badgeConfig[type];
  
  if (!config) return null;
  
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${config.className}`}>
      {config.label}
    </span>
  );
}
