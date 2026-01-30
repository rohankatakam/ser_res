/**
 * Serafis Mock API Client
 */

const API_BASE = 'http://localhost:8000';

export async function fetchDiscover(userId) {
  const response = await fetch(`${API_BASE}/api/recommendations/discover?user_id=${userId}`);
  if (!response.ok) throw new Error('Failed to fetch discover');
  return response.json();
}

export async function fetchInsightsForYou(userId, limit = 10) {
  const response = await fetch(`${API_BASE}/api/recommendations/insights-for-you?user_id=${userId}&limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch insights');
  return response.json();
}

export async function fetchHighestSignal(userId, limit = 10) {
  const response = await fetch(`${API_BASE}/api/recommendations/highest-signal?user_id=${userId}&limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch highest signal');
  return response.json();
}

export async function fetchNonConsensus(userId, limit = 10) {
  const response = await fetch(`${API_BASE}/api/recommendations/non-consensus?user_id=${userId}&limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch non-consensus');
  return response.json();
}

export async function fetchNewFromShows(userId, limit = 10) {
  const response = await fetch(`${API_BASE}/api/recommendations/new-from-shows?user_id=${userId}&limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch new from shows');
  return response.json();
}

export async function fetchTrending(userId, category, limit = 10) {
  const response = await fetch(`${API_BASE}/api/recommendations/trending/${encodeURIComponent(category)}?user_id=${userId}&limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch trending');
  return response.json();
}

export async function markNotInterested(userId, episodeId) {
  const response = await fetch(`${API_BASE}/api/feedback/not-interested`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, episode_id: episodeId })
  });
  if (!response.ok) throw new Error('Failed to mark not interested');
  return response.json();
}

export async function fetchApiInfo() {
  const response = await fetch(`${API_BASE}/`);
  if (!response.ok) throw new Error('Failed to fetch API info');
  return response.json();
}
