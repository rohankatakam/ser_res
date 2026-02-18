/**
 * Simple login / create user screen (no password).
 * Username: one word, no spaces or special characters.
 * Create mode: optional category interests for cold-start recommendations.
 */

import { useState, useEffect } from 'react';
import { userEnterByLogin, userEnterByCreate, getCategories } from '../api';

const USERNAME_REGEX = /^[a-zA-Z0-9_]+$/;

// Fallback if API not available
const DEFAULT_CATEGORIES = [
  'Technology & AI',
  'Startups, Growth and Founder Journeys',
  'Macro, Investing & Market Trends',
  'Crypto & Web3',
  'Regulation & Policy',
  'Venture & Private Markets',
  'Culture, Society & Wellbeing',
];

function validateUsername(value) {
  const trimmed = (value || '').trim();
  if (!trimmed) return 'Enter a username';
  if (!USERNAME_REGEX.test(trimmed)) {
    return 'Use only letters, numbers, and underscores (no spaces or special characters)';
  }
  return null;
}

export default function LoginScreen({ onSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' | 'create'
  const [username, setUsername] = useState('');
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    getCategories().then((res) => res.categories && setCategories(res.categories)).catch(() => {});
  }, []);

  const toggleCategory = (cat) => {
    setSelectedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    const validation = validateUsername(username);
    if (validation) {
      setError(validation);
      return;
    }
    const trimmed = username.trim();
    setLoading(true);
    try {
      if (mode === 'login') {
        const user = await userEnterByLogin(trimmed.toLowerCase());
        onSuccess(user);
      } else {
        const result = await userEnterByCreate(trimmed, selectedCategories);
        if (result.created) {
          setMessage('Account created. Logging you in...');
        } else {
          setMessage('User already exists. Logging you in...');
        }
        setTimeout(() => onSuccess(result), 400);
      }
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl bg-slate-800 border border-slate-700 p-6 shadow-xl">
        <h1 className="text-xl font-semibold text-white mb-1">Serafis</h1>
        <p className="text-slate-400 text-sm mb-6">Enter your username to continue</p>

        <div className="flex gap-2 mb-4">
          <button
            type="button"
            onClick={() => { setMode('login'); setError(''); setMessage(''); setSelectedCategories([]); }}
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-lg ${mode === 'login' ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'}`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => { setMode('create'); setError(''); setMessage(''); }}
            className={`flex-1 py-2 px-3 text-sm font-medium rounded-lg ${mode === 'create' ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'}`}
          >
            Create User
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <label className="block text-slate-300 text-sm mb-1">
            {mode === 'login' ? 'Username (user id)' : 'Username'}
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={mode === 'create' ? 'e.g. alice' : 'Enter your username'}
            className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            autoComplete="username"
            disabled={loading}
          />
          {mode === 'create' && (
            <div className="mt-4">
              <label className="block text-slate-300 text-sm mb-2">
                Pick topics you care about (optional — improves first recommendations)
              </label>
              <div className="max-h-40 overflow-y-auto rounded-lg bg-slate-700 border border-slate-600 p-2 space-y-1.5">
                {categories.map((cat) => (
                  <label
                    key={cat}
                    className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white"
                  >
                    <input
                      type="checkbox"
                      checked={selectedCategories.includes(cat)}
                      onChange={() => toggleCategory(cat)}
                      className="rounded border-slate-500 bg-slate-600 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm">{cat}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
          {error && (
            <p className="mt-2 text-sm text-red-400" role="alert">
              {error}
            </p>
          )}
          {message && (
            <p className="mt-2 text-sm text-green-400" role="status">
              {message}
            </p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="mt-4 w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
          >
            {loading ? '...' : mode === 'login' ? 'Login' : 'Create User'}
          </button>
        </form>

        <p className="mt-4 text-xs text-slate-500">
          One word only: letters, numbers, and underscores. No spaces or special characters.
        </p>
      </div>
    </div>
  );
}
