/**
 * GoogleSetupWizard - Step-by-step Google OAuth setup guide
 */
import { useState, useEffect } from 'react';
import { authApi } from '../api/client';

export default function GoogleSetupWizard({ onComplete, onClose }) {
    const [step, setStep] = useState(1);
    const [instructions, setInstructions] = useState(null);
    const [clientId, setClientId] = useState('');
    const [clientSecret, setClientSecret] = useState('');
    const [showSecret, setShowSecret] = useState(false);
    const [testing, setTesting] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [testResult, setTestResult] = useState(null);

    useEffect(() => {
        loadInstructions();
    }, []);

    const loadInstructions = async () => {
        try {
            const data = await authApi.getSetupInstructions();
            setInstructions(data);
        } catch (err) {
            setError('Failed to load setup instructions');
        }
    };

    const handleTest = async () => {
        if (!clientId || !clientSecret) {
            setError('Please enter both Client ID and Client Secret');
            return;
        }

        setTesting(true);
        setError(null);
        setTestResult(null);

        try {
            const result = await authApi.testCredentials(clientId, clientSecret);
            setTestResult(result);
            if (result.valid) {
                setStep(4);
            }
        } catch (err) {
            setError(err.message || 'Failed to test credentials');
        } finally {
            setTesting(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);

        try {
            await authApi.saveCredentials(clientId, clientSecret);
            onComplete?.();
        } catch (err) {
            setError(err.message || 'Failed to save credentials');
        } finally {
            setSaving(false);
        }
    };

    const totalSteps = 4;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-surface-800 rounded-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-surface-700">
                    <div className="flex items-center gap-3">
                        <span className="text-3xl">🔐</span>
                        <div>
                            <h2 className="text-xl font-bold text-white">Google Calendar Setup</h2>
                            <p className="text-sm text-surface-400">Step {step} of {totalSteps}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-surface-400 hover:text-white text-2xl"
                    >
                        ✕
                    </button>
                </div>

                {/* Progress Bar */}
                <div className="px-6 py-3">
                    <div className="h-2 bg-surface-700 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary-500 transition-all duration-300"
                            style={{ width: `${(step / totalSteps) * 100}%` }}
                        />
                    </div>
                </div>

                {/* Content */}
                <div className="p-6">
                    {error && (
                        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Step 1: Introduction */}
                    {step === 1 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white">Why Connect Google Calendar?</h3>
                            <p className="text-surface-300">
                                Connecting your Google Calendar allows LifePilot to:
                            </p>
                            <ul className="space-y-2 text-surface-300">
                                <li className="flex items-start gap-2">
                                    <span className="text-green-400">✓</span>
                                    <span>See your existing appointments when planning tasks</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-green-400">✓</span>
                                    <span>Add LifePilot tasks to your calendar</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-green-400">✓</span>
                                    <span>Find free time blocks for focused work</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-green-400">✓</span>
                                    <span>Keep everything in sync automatically</span>
                                </li>
                            </ul>
                            <div className="bg-surface-700/50 rounded-lg p-4 mt-4">
                                <p className="text-sm text-surface-400">
                                    <strong className="text-white">Privacy Note:</strong> Your calendar data stays on your device.
                                    LifePilot never sends your events to external servers.
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Step 2: Create Google Cloud Project */}
                    {step === 2 && instructions && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white">Create Google OAuth Credentials</h3>
                            <p className="text-surface-300 text-sm">
                                Follow these steps in Google Cloud Console:
                            </p>
                            <div className="space-y-3">
                                {instructions.steps.slice(0, 6).map((s, i) => (
                                    <div key={i} className="flex gap-3 bg-surface-700/30 rounded-lg p-3">
                                        <span className="w-6 h-6 bg-primary-500/20 text-primary-400 rounded-full 
                                                       flex items-center justify-center text-sm font-medium flex-shrink-0">
                                            {s.step}
                                        </span>
                                        <div className="flex-1">
                                            <p className="text-white font-medium">{s.title}</p>
                                            <p className="text-surface-400 text-sm">{s.description}</p>
                                            {s.code && (
                                                <code className="mt-1 block text-xs bg-surface-900 p-2 rounded text-primary-300 break-all">
                                                    {s.code}
                                                </code>
                                            )}
                                            {s.link && (
                                                <a
                                                    href={s.link}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-primary-400 hover:text-primary-300 text-sm mt-1 inline-block"
                                                >
                                                    Open in Google Cloud Console →
                                                </a>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Enter Credentials */}
                    {step === 3 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-white">Enter Your Credentials</h3>
                            <p className="text-surface-300 text-sm">
                                Copy the Client ID and Client Secret from Google Cloud Console:
                            </p>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm text-surface-300 mb-2">
                                        Client ID
                                    </label>
                                    <input
                                        type="text"
                                        value={clientId}
                                        onChange={(e) => setClientId(e.target.value)}
                                        placeholder="xxxxxxxxxx.apps.googleusercontent.com"
                                        className="w-full bg-surface-900 border border-surface-600 rounded-lg px-4 py-3
                                                   text-white placeholder-surface-500 focus:border-primary-500 focus:outline-none"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm text-surface-300 mb-2">
                                        Client Secret
                                    </label>
                                    <div className="relative">
                                        <input
                                            type={showSecret ? 'text' : 'password'}
                                            value={clientSecret}
                                            onChange={(e) => setClientSecret(e.target.value)}
                                            placeholder="GOCSPX-xxxxxxxxxx"
                                            className="w-full bg-surface-900 border border-surface-600 rounded-lg px-4 py-3 pr-12
                                                       text-white placeholder-surface-500 focus:border-primary-500 focus:outline-none"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowSecret(!showSecret)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-white"
                                        >
                                            {showSecret ? '🙈' : '👁️'}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {testResult && (
                                <div className={`p-3 rounded-lg text-sm ${testResult.valid
                                        ? 'bg-green-500/10 border border-green-500/30 text-green-300'
                                        : 'bg-red-500/10 border border-red-500/30 text-red-300'
                                    }`}>
                                    {testResult.valid ? '✓ ' : '✗ '}
                                    {testResult.message || testResult.error}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 4: Complete */}
                    {step === 4 && (
                        <div className="space-y-4 text-center py-8">
                            <div className="text-6xl">✅</div>
                            <h3 className="text-xl font-semibold text-white">Credentials Verified!</h3>
                            <p className="text-surface-300">
                                Your Google OAuth credentials are valid. Click "Save & Connect" to
                                save these credentials and connect your Google account.
                            </p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-surface-700">
                    <button
                        onClick={() => setStep(Math.max(1, step - 1))}
                        disabled={step === 1}
                        className="px-4 py-2 text-surface-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        ← Back
                    </button>

                    <div className="flex gap-2">
                        {step < 3 && (
                            <button
                                onClick={() => setStep(step + 1)}
                                className="px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
                            >
                                Next →
                            </button>
                        )}

                        {step === 3 && (
                            <button
                                onClick={handleTest}
                                disabled={testing || !clientId || !clientSecret}
                                className="px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg 
                                           transition-colors disabled:opacity-50"
                            >
                                {testing ? 'Testing...' : 'Test Credentials'}
                            </button>
                        )}

                        {step === 4 && (
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="px-6 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg 
                                           transition-colors disabled:opacity-50"
                            >
                                {saving ? 'Saving...' : 'Save & Connect'}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
