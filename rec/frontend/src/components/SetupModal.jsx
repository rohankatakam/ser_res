/**
 * Setup Modal - Appears when API keys are missing from backend .env
 * 
 * Shows which keys are missing and provides instructions to configure them.
 * Cannot be dismissed if OpenAI key is missing (required for embeddings).
 */

import { useState, useEffect } from 'react';
import { getApiKeyStatus } from '../api';

export default function SetupModal({ isOpen, onClose, initialStatus }) {
    const [status, setStatus] = useState(initialStatus);
    const [checking, setChecking] = useState(false);
    const [error, setError] = useState(null);

    const checkStatus = async () => {
        setChecking(true);
        setError(null);
        try {
            const newStatus = await getApiKeyStatus();
            setStatus(newStatus);

            // Auto-close if OpenAI is now configured
            if (newStatus.openai_configured && onClose) {
                onClose();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setChecking(false);
        }
    };

    if (!isOpen) return null;

    const canDismiss = status?.openai_configured;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
            <div className="bg-slate-800 border border-slate-700 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="p-6 border-b border-slate-700">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="text-3xl">⚙️</span>
                            <div>
                                <h2 className="text-2xl font-bold text-white">API Keys Required</h2>
                                <p className="text-slate-400 text-sm mt-1">
                                    Configure API keys to use Serafis
                                </p>
                            </div>
                        </div>
                        {canDismiss && (
                            <button
                                onClick={onClose}
                                className="text-slate-400 hover:text-white transition-colors"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        )}
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Error Banner */}
                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Status Overview */}
                    <div className="space-y-3">
                        <h3 className="text-lg font-semibold text-white">Configuration Status</h3>

                        {/* OpenAI Key */}
                        <div className={`p-4 rounded-lg border ${status?.openai_configured
                                ? 'bg-green-500/10 border-green-500/30'
                                : 'bg-red-500/10 border-red-500/30'
                            }`}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <span className="text-2xl">
                                        {status?.openai_configured ? '✅' : '❌'}
                                    </span>
                                    <div>
                                        <p className="font-medium text-white">OpenAI API Key</p>
                                        <p className="text-sm text-slate-400">Required for generating embeddings</p>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${status?.openai_configured
                                        ? 'bg-green-500 text-white'
                                        : 'bg-red-500 text-white'
                                    }`}>
                                    {status?.openai_configured ? 'Configured' : 'Required'}
                                </span>
                            </div>
                        </div>

                        {/* Gemini Key */}
                        <div className={`p-4 rounded-lg border ${status?.gemini_configured
                                ? 'bg-green-500/10 border-green-500/30'
                                : 'bg-slate-700/30 border-slate-600'
                            }`}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <span className="text-2xl">
                                        {status?.gemini_configured ? '✅' : 'ℹ️'}
                                    </span>
                                    <div>
                                        <p className="font-medium text-white">Gemini API Key</p>
                                        <p className="text-sm text-slate-400">Optional for LLM evaluation</p>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${status?.gemini_configured
                                        ? 'bg-green-500 text-white'
                                        : 'bg-slate-600 text-slate-300'
                                    }`}>
                                    {status?.gemini_configured ? 'Configured' : 'Optional'}
                                </span>
                            </div>
                        </div>

                        {/* Anthropic Key */}
                        <div className={`p-4 rounded-lg border ${status?.anthropic_configured
                                ? 'bg-green-500/10 border-green-500/30'
                                : 'bg-slate-700/30 border-slate-600'
                            }`}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <span className="text-2xl">
                                        {status?.anthropic_configured ? '✅' : 'ℹ️'}
                                    </span>
                                    <div>
                                        <p className="font-medium text-white">Anthropic API Key</p>
                                        <p className="text-sm text-slate-400">Optional for LLM evaluation with Claude</p>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${status?.anthropic_configured
                                        ? 'bg-green-500 text-white'
                                        : 'bg-slate-600 text-slate-300'
                                    }`}>
                                    {status?.anthropic_configured ? 'Configured' : 'Optional'}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Instructions */}
                    {!status?.openai_configured && (
                        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                            <h4 className="text-amber-400 font-semibold mb-3 flex items-center gap-2">
                                <span>📝</span>
                                Setup Instructions
                            </h4>
                            <ol className="space-y-2 text-sm text-amber-200">
                                <li className="flex gap-2">
                                    <span className="font-bold">1.</span>
                                    <span>
                                        Edit your <code className="bg-slate-900/50 px-1.5 py-0.5 rounded text-amber-300">.env</code> file:
                                        <br />
                                        <code className="block mt-1 bg-slate-900/50 px-2 py-1 rounded text-xs text-amber-300 font-mono">
                                            /Users/rohankatakam/Documents/serafis/rec/.env
                                        </code>
                                    </span>
                                </li>
                                <li className="flex gap-2">
                                    <span className="font-bold">2.</span>
                                    <span>
                                        Add your API keys:
                                        <br />
                                        <code className="block mt-1 bg-slate-900/50 px-2 py-1 rounded text-xs text-amber-300 font-mono">
                                            OPENAI_API_KEY=sk-your-key-here
                                        </code>
                                    </span>
                                </li>
                                <li className="flex gap-2">
                                    <span className="font-bold">3.</span>
                                    <span>
                                        Restart the backend:
                                        <br />
                                        <code className="block mt-1 bg-slate-900/50 px-2 py-1 rounded text-xs text-amber-300 font-mono">
                                            docker-compose restart backend
                                        </code>
                                    </span>
                                </li>
                                <li className="flex gap-2">
                                    <span className="font-bold">4.</span>
                                    <span>Click "Refresh Status" below</span>
                                </li>
                            </ol>
                        </div>
                    )}

                    {/* Get API Keys Links */}
                    <div className="p-4 bg-slate-700/30 border border-slate-600 rounded-lg">
                        <h4 className="text-white font-semibold mb-3">Get API Keys</h4>
                        <div className="space-y-2 text-sm">
                            <a
                                href="https://platform.openai.com/api-keys"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition-colors"
                            >
                                <span>🔗</span>
                                <span>OpenAI API Keys</span>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                            </a>
                            <a
                                href="https://aistudio.google.com/apikey"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition-colors"
                            >
                                <span>🔗</span>
                                <span>Gemini API Keys</span>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                            </a>
                            <a
                                href="https://console.anthropic.com/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition-colors"
                            >
                                <span>🔗</span>
                                <span>Anthropic API Keys</span>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                            </a>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-slate-700 flex items-center justify-between">
                    <p className="text-sm text-slate-400">
                        {canDismiss
                            ? 'OpenAI key configured. You can now use Serafis!'
                            : 'OpenAI key required to continue'}
                    </p>
                    <div className="flex gap-3">
                        <button
                            onClick={checkStatus}
                            disabled={checking}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${checking
                                    ? 'bg-indigo-600/50 text-indigo-300 cursor-not-allowed'
                                    : 'bg-indigo-600 text-white hover:bg-indigo-500'
                                }`}
                        >
                            {checking ? 'Checking...' : 'Refresh Status'}
                        </button>
                        {canDismiss && (
                            <button
                                onClick={onClose}
                                className="px-4 py-2 bg-slate-700 text-white rounded-lg font-medium hover:bg-slate-600 transition-colors"
                            >
                                Continue
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
