/**
 * Modal for editing user category interests.
 * Pre-populates from user's current category_interests; saves via PATCH.
 */

import { useState, useEffect } from 'react';
import { getCategories, getUser, updateCategoryInterests } from '../api';

const DEFAULT_CATEGORIES = [
  'Technology & AI',
  'Startups, Growth and Founder Journeys',
  'Macro, Investing & Market Trends',
  'Crypto & Web3',
  'Regulation & Policy',
  'Venture & Private Markets',
  'Culture, Society & Wellbeing',
];

export default function InterestsModal({ userId, onClose, onSaved }) {
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getCategories()
      .then((res) => res.categories && setCategories(res.categories))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError('');
    getUser(userId)
      .then((u) => {
        setSelectedCategories(u.category_interests || []);
      })
      .catch((e) => {
        setError(e.message || 'Failed to load interests');
        setSelectedCategories([]);
      })
      .finally(() => setLoading(false));
  }, [userId]);

  const toggleCategory = (cat) => {
    setSelectedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  };

  const handleSave = async () => {
    if (!userId) return;
    setSaving(true);
    setError('');
    try {
      await updateCategoryInterests(userId, selectedCategories);
      onSaved?.();
      onClose?.();
    } catch (e) {
      setError(e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl bg-slate-800 border border-slate-700 p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-white mb-2">Edit topic interests</h2>
        <p className="text-slate-400 text-sm mb-4">
          Pick topics you care about. This improves your first recommendations and keeps diversity in your feed.
        </p>
        {loading ? (
          <p className="text-slate-400 text-sm py-4">Loading...</p>
        ) : (
          <>
            <div className="max-h-48 overflow-y-auto rounded-lg bg-slate-700 border border-slate-600 p-2 space-y-1.5 mb-4">
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
            {error && (
              <p className="mb-3 text-sm text-red-400" role="alert">
                {error}
              </p>
            )}
          </>
        )}
        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={loading || saving}
            className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
