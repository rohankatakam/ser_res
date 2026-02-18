/**
 * Serafis API Client — V1.1 Session Pool (Option C)
 * 
 * Session-based recommendation API with:
 * - Create Session: Compute rankings once, store queue
 * - Load More: Get next N from queue (no recomputation)
 * - Refresh: Create new session with fresh computation
 * - Engage: Mark episode as engaged
 */

// Use relative URL in production (nginx proxies /api to backend)
// Use localhost:8000 in development
const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:8000';

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
 * @param {string} [userId] - Optional user ID (for Firestore engagement store)
 * @returns {Promise<Object>} Session response with episodes, session_id, queue info
 */
export async function createSession(engagements = [], excludedIds = [], userId = null) {
  const body = { engagements, excluded_ids: excludedIds };
  if (userId != null && userId !== '') body.user_id = String(userId);

  const response = await fetch(`${API_BASE}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create session');
  }
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
 * @param {string} [userId] - Optional user ID (for Firestore persistence)
 * @returns {Promise<Object>} Engagement confirmation
 */
export async function engageEpisode(sessionId, episodeId, type = 'click', userId = null) {
  const body = {
    episode_id: episodeId,
    type,
    timestamp: new Date().toISOString()
  };
  if (userId != null && userId !== '') body.user_id = String(userId);

  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/engage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
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

// ============================================================================
// Configuration Endpoints (new evaluation server)
// ============================================================================

/**
 * Get current config status
 */
export async function getConfigStatus() {
  const response = await fetch(`${API_BASE}/api/config/status`);
  if (!response.ok) throw new Error('Failed to get config status');
  return response.json();
}

/**
 * List available algorithms
 */
export async function listAlgorithms() {
  const response = await fetch(`${API_BASE}/api/config/algorithms`);
  if (!response.ok) throw new Error('Failed to list algorithms');
  return response.json();
}

/**
 * List available datasets
 */
export async function listDatasets() {
  const response = await fetch(`${API_BASE}/api/config/datasets`);
  if (!response.ok) throw new Error('Failed to list datasets');
  return response.json();
}

/**
 * Get API key configuration status.
 * 
 * Checks which API keys are configured in the backend .env file.
 * Used by frontend to show setup modal when keys are missing.
 * 
 * @returns {Promise<Object>} Status object with openai_configured, gemini_configured, etc.
 */
export async function getApiKeyStatus() {
  const response = await fetch(`${API_BASE}/api/config/api-keys/status`);
  if (!response.ok) throw new Error('Failed to get API key status');
  return response.json();
}

/**
 * Validate algorithm-dataset compatibility
 */
export async function validateCompatibility(algorithmFolder, datasetFolder) {
  const response = await fetch(`${API_BASE}/api/config/validate?algorithm_folder=${encodeURIComponent(algorithmFolder)}&dataset_folder=${encodeURIComponent(datasetFolder)}`);
  if (!response.ok) throw new Error('Failed to validate');
  return response.json();
}

/**
 * Load algorithm and dataset configuration
 */
export async function loadConfiguration(algorithmFolder, datasetFolder, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (options.openaiKey) {
    headers['X-OpenAI-Key'] = options.openaiKey;
  }

  const response = await fetch(`${API_BASE}/api/config/load`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      algorithm: algorithmFolder,
      dataset: datasetFolder,
      generate_embeddings: options.generateEmbeddings !== false
    })
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    // Handle validation errors (array of objects) or string errors
    let errorMsg = 'Failed to load configuration';
    if (typeof err.detail === 'string') {
      errorMsg = err.detail;
    } else if (Array.isArray(err.detail)) {
      errorMsg = err.detail.map(e => e.msg || JSON.stringify(e)).join(', ');
    }
    throw new Error(errorMsg);
  }
  return response.json();
}

/**
 * Check embedding cache status
 */
export async function getEmbeddingStatus(algorithmFolder, datasetFolder) {
  const response = await fetch(
    `${API_BASE}/api/embeddings/status?algorithm_folder=${encodeURIComponent(algorithmFolder)}&dataset_folder=${encodeURIComponent(datasetFolder)}`
  );
  if (!response.ok) throw new Error('Failed to get embedding status');
  return response.json();
}

/**
 * Poll embedding status until embeddings are ready or timeout.
 * 
 * @param {string} algorithmFolder - Algorithm folder name
 * @param {string} datasetFolder - Dataset folder name
 * @param {number} maxWaitMs - Maximum time to wait in milliseconds (default: 120000ms = 2 minutes)
 * @param {number} pollIntervalMs - Interval between polls in milliseconds (default: 2000ms)
 * @returns {Promise<Object>} Final embedding status
 */
export async function pollEmbeddingStatus(algorithmFolder, datasetFolder, maxWaitMs = 120000, pollIntervalMs = 2000) {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    const status = await getEmbeddingStatus(algorithmFolder, datasetFolder);

    // Check if embeddings are ready
    if (status.cached && status.count > 0) {
      return status;
    }

    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
  }

  // Timeout reached
  throw new Error('Embedding generation timeout - please check status manually');
}

// ============================================================================
// Evaluation Endpoints
// ============================================================================

/**
 * List evaluation user profiles
 */
export async function listProfiles() {
  const response = await fetch(`${API_BASE}/api/evaluation/profiles`);
  if (!response.ok) throw new Error('Failed to list profiles');
  return response.json();
}

/**
 * Get a specific profile
 */
export async function getProfile(profileId) {
  const response = await fetch(`${API_BASE}/api/evaluation/profiles/${encodeURIComponent(profileId)}`);
  if (!response.ok) throw new Error('Profile not found');
  return response.json();
}

/**
 * List test cases
 */
export async function listTestCases() {
  const response = await fetch(`${API_BASE}/api/evaluation/test-cases`);
  if (!response.ok) throw new Error('Failed to list test cases');
  return response.json();
}

/**
 * Get a specific test case
 */
export async function getTestCase(testId) {
  const response = await fetch(`${API_BASE}/api/evaluation/test-cases/${encodeURIComponent(testId)}`);
  if (!response.ok) throw new Error('Test case not found');
  return response.json();
}

/**
 * Run a single test with multi-LLM evaluation
 */
export async function runTest(testId, options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (options.openaiKey) {
    headers['X-OpenAI-Key'] = options.openaiKey;
  }
  if (options.geminiKey) {
    headers['X-Gemini-Key'] = options.geminiKey;
  }
  if (options.anthropicKey) {
    headers['X-Anthropic-Key'] = options.anthropicKey;
  }

  const response = await fetch(`${API_BASE}/api/evaluation/run`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      test_id: testId
      // Note: LLM evaluation always runs (no with_llm flag)
    })
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to run test');
  }
  return response.json();
}

/**
 * Run all tests with multi-LLM evaluation
 */
export async function runAllTests(options = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (options.openaiKey) {
    headers['X-OpenAI-Key'] = options.openaiKey;
  }
  if (options.geminiKey) {
    headers['X-Gemini-Key'] = options.geminiKey;
  }
  if (options.anthropicKey) {
    headers['X-Anthropic-Key'] = options.anthropicKey;
  }

  const response = await fetch(`${API_BASE}/api/evaluation/run-all`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      save_report: options.saveReport !== false
      // Note: LLM evaluation always runs (no with_llm flag)
    })
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to run tests');
  }
  return response.json();
}

/**
 * Get judge configuration (which LLM providers are enabled, N samples, etc.)
 */
export async function getJudgeConfig() {
  const response = await fetch(`${API_BASE}/api/evaluation/judge-config`);
  if (!response.ok) throw new Error('Failed to get judge configuration');
  return response.json();
}

/**
 * Update judge configuration
 */
export async function updateJudgeConfig(config) {
  const response = await fetch(`${API_BASE}/api/evaluation/judge-config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to update judge configuration');
  }
  return response.json();
}

/**
 * List test reports
 */
export async function listReports() {
  const response = await fetch(`${API_BASE}/api/evaluation/reports`);
  if (!response.ok) throw new Error('Failed to list reports');
  return response.json();
}

/**
 * Get a specific report
 */
export async function getReport(reportId) {
  const response = await fetch(`${API_BASE}/api/evaluation/reports/${encodeURIComponent(reportId)}`);
  if (!response.ok) throw new Error('Report not found');
  return response.json();
}

// ============================================================================
// User (simple login / create by name — no password)
// ============================================================================

/**
 * Login: enter with user id (username). Returns user or throws if user does not exist.
 * @param {string} userId - Username (one word, no spaces)
 * @returns {Promise<{ user_id, display_name }>}
 */
export async function userEnterByLogin(userId) {
  const response = await fetch(`${API_BASE}/api/user/enter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId })
  });
  if (response.status === 404) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'User does not exist');
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  return response.json();
}

/**
 * Create user (or log in if name already exists). Username: one word, no spaces or special characters.
 * @param {string} displayName - Display name for the new user
 * @returns {Promise<{ user_id, display_name, created }>} created === true if new user was created
 */
export async function userEnterByCreate(displayName) {
  const response = await fetch(`${API_BASE}/api/user/enter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ display_name: displayName })
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Create user failed');
  }
  return response.json();
}

/**
 * Get engagements for a user from the backend (Firestore when configured).
 *
 * @param {string} userId - User ID
 * @returns {Promise<{ engagements: Array }>}
 */
export async function getEngagements(userId) {
  if (!userId) return { engagements: [] };
  const params = new URLSearchParams({ user_id: userId });
  const response = await fetch(`${API_BASE}/api/user/engagements?${params}`);
  if (!response.ok) throw new Error('Failed to get engagements');
  return response.json();
}

/**
 * Reset (delete) all engagements for a user. Use after "Reset" in the app.
 *
 * @param {string} userId - User ID
 * @returns {Promise<Object>}
 */
export async function resetEngagements(userId) {
  if (!userId) return { status: 'ok' };
  const params = new URLSearchParams({ user_id: userId });
  const response = await fetch(`${API_BASE}/api/user/engagements/reset?${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!response.ok) throw new Error('Failed to reset engagements');
  return response.json();
}
