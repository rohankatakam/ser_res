/**
 * Serafis API Client — V1.1 Session Pool (Option C)
 * 
 * Session-based recommendation API with:
 * - Create Session: Compute rankings once, store queue
 * - Load More: Get next N from queue (no recomputation)
 * - Refresh: Create new session with fresh computation
 * - Engage: Mark episode as engaged
 */

const API_BASE = 'http://localhost:8000';

// ============================================================================
// Session Endpoints (Option C)
// ============================================================================

/**
 * Create a new recommendation session.
 * 
 * Computes user vector from engagements, ranks all candidates,
 * and returns the first page of recommendations.
 * 
 * @param {Array} engagements - User's engagement history [{episode_id, type, timestamp}]
 * @param {Array} excludedIds - Episode IDs to exclude
 * @returns {Promise<Object>} Session response with episodes, session_id, queue info
 */
export async function createSession(engagements = [], excludedIds = []) {
  const response = await fetch(`${API_BASE}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      engagements,
      excluded_ids: excludedIds
    })
  });
  
  if (!response.ok) throw new Error('Failed to create session');
  return response.json();
}

/**
 * Get session info (without loading more episodes).
 * 
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} Session status
 */
export async function getSessionInfo(sessionId) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
  if (!response.ok) throw new Error('Session not found');
  return response.json();
}

/**
 * Load more episodes from the session queue.
 * 
 * Returns the next N episodes from the pre-computed queue.
 * NO recomputation happens - this is deterministic pagination.
 * 
 * @param {string} sessionId - Session ID
 * @param {number} limit - Number of episodes to load (default 10)
 * @returns {Promise<Object>} Session response with next episodes
 */
export async function loadMore(sessionId, limit = 10) {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/next`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limit })
  });
  
  if (!response.ok) throw new Error('Failed to load more');
  return response.json();
}

/**
 * Record an engagement within the session.
 * 
 * The engaged episode is removed from the queue (won't appear in load_more).
 * 
 * @param {string} sessionId - Session ID
 * @param {string} episodeId - Episode ID
 * @param {string} type - Engagement type ('click', 'bookmark')
 * @returns {Promise<Object>} Engagement confirmation
 */
export async function engageEpisode(sessionId, episodeId, type = 'click') {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/engage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      episode_id: episodeId,
      type,
      timestamp: new Date().toISOString()
    })
  });
  
  if (!response.ok) throw new Error('Failed to record engagement');
  return response.json();
}

// ============================================================================
// Legacy Endpoints (kept for compatibility)
// ============================================================================

/**
 * Legacy: Get "For You" recommendations (creates session, returns first page).
 * @deprecated Use createSession instead
 */
export async function fetchForYou(engagements = [], excludedIds = []) {
  const response = await fetch(`${API_BASE}/api/recommendations/for-you`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      engagements,
      excluded_ids: excludedIds
    })
  });
  
  if (!response.ok) throw new Error('Failed to fetch For You recommendations');
  return response.json();
}

/**
 * Get all episodes with pagination.
 * 
 * @param {number} limit - Maximum episodes to return
 * @param {number} offset - Offset for pagination
 * @returns {Promise<Object>} Episodes list with total count
 */
export async function fetchEpisodes(limit = null, offset = 0) {
  const params = new URLSearchParams({ offset: offset.toString() });
  if (limit) params.set('limit', limit.toString());
  
  const response = await fetch(`${API_BASE}/api/episodes?${params}`);
  if (!response.ok) throw new Error('Failed to fetch episodes');
  return response.json();
}

/**
 * Get full episode details by ID.
 * 
 * @param {string} episodeId - Episode ID or content_id
 * @returns {Promise<Object>} Full episode details
 */
export async function fetchEpisode(episodeId) {
  const response = await fetch(`${API_BASE}/api/episodes/${encodeURIComponent(episodeId)}`);
  if (!response.ok) throw new Error('Failed to fetch episode');
  return response.json();
}

/**
 * Get all series.
 * 
 * @returns {Promise<Object>} Series list
 */
export async function fetchSeries() {
  const response = await fetch(`${API_BASE}/api/series`);
  if (!response.ok) throw new Error('Failed to fetch series');
  return response.json();
}

/**
 * Get API statistics.
 * 
 * @returns {Promise<Object>} Stats including episode counts, embeddings, etc.
 */
export async function fetchStats() {
  const response = await fetch(`${API_BASE}/api/stats`);
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
}

export async function fetchApiInfo() {
  const response = await fetch(`${API_BASE}/`);
  if (!response.ok) throw new Error('Failed to fetch API info');
  return response.json();
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Check if API is running.
 * 
 * @returns {Promise<boolean>}
 */
export async function checkApiHealth() {
  try {
    const response = await fetch(`${API_BASE}/`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Format an engagement for API.
 * 
 * @param {Object} episode - Episode object
 * @param {string} type - Engagement type ('click', 'bookmark', 'listen')
 * @returns {Object} Formatted engagement
 */
export function createEngagement(episode, type = 'click') {
  return {
    episode_id: episode.id || episode.content_id,
    type,
    timestamp: new Date().toISOString()
  };
}
