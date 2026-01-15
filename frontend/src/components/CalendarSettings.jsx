/**
 * CalendarSettings - Calendar integration management interface with OAuth setup
 */
import { useState, useEffect } from 'react';
import { calendarApi, authApi } from '../api/client';
import GoogleSetupWizard from './GoogleSetupWizard';
import NotificationSettings from './NotificationSettings';

const PROVIDERS = [
    { id: 'google', name: 'Google Calendar', icon: '📅', color: 'bg-blue-500' }
];

export default function CalendarSettings() {
    const [connections, setConnections] = useState([]);
    const [syncLogs, setSyncLogs] = useState({});
    const [preferences, setPreferences] = useState(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState({});
    const [error, setError] = useState(null);

    // OAuth status
    const [oauthStatus, setOauthStatus] = useState(null);
    const [showSetupWizard, setShowSetupWizard] = useState(false);
    const [connecting, setConnecting] = useState(false);

    useEffect(() => {
        fetchData();

        // Listen for OAuth popup success
        const handleMessage = (event) => {
            if (event.data?.type === 'oauth_success') {
                fetchData();
            } else if (event.data?.type === 'oauth_error') {
                setError(event.data.error);
            }
        };
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [status, prefs] = await Promise.all([
                authApi.getStatus(),
                calendarApi.getPreferences()
            ]);

            setOauthStatus(status);
            setConnections(status.google?.accounts || []);
            setPreferences(prefs);

            // Fetch logs for each connection
            const logsMap = {};
            for (const conn of (status.google?.accounts || [])) {
                try {
                    logsMap[conn.id] = await calendarApi.getSyncLogs(conn.id, 5);
                } catch (e) {
                    logsMap[conn.id] = [];
                }
            }
            setSyncLogs(logsMap);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleConnect = async (providerId) => {
        if (!oauthStatus?.google?.configured) {
            setShowSetupWizard(true);
            return;
        }

        setConnecting(true);
        try {
            const result = await authApi.initiateGoogle();
            // Open OAuth in popup window
            const popup = window.open(
                result.auth_url,
                'google_oauth',
                'width=600,height=700,left=200,top=100'
            );

            // Poll for popup close
            const pollTimer = setInterval(() => {
                if (popup?.closed) {
                    clearInterval(pollTimer);
                    setConnecting(false);
                    fetchData();
                }
            }, 500);
        } catch (err) {
            setError(err.message || 'Failed to start OAuth');
            setConnecting(false);
        }
    };

    const handleDisconnect = async (connectionId) => {
        if (!confirm('Are you sure you want to disconnect this calendar?')) return;

        try {
            await authApi.deleteConnection(connectionId);
            fetchData();
        } catch (err) {
            setError(err.message);
        }
    };

    const handleSync = async (connectionId, direction = 'bidirectional') => {
        setSyncing(prev => ({ ...prev, [connectionId]: true }));
        try {
            await calendarApi.triggerSync(connectionId, direction);
            // Refresh logs
            const logs = await calendarApi.getSyncLogs(connectionId, 5);
            setSyncLogs(prev => ({ ...prev, [connectionId]: logs }));
            // Refresh connections
            fetchData();
        } catch (err) {
            setError(err.message);
        } finally {
            setSyncing(prev => ({ ...prev, [connectionId]: false }));
        }
    };

    const handlePreferenceChange = async (key, value) => {
        const updated = { ...preferences, [key]: value };
        setPreferences(updated);
        try {
            await calendarApi.updatePreferences(updated);
        } catch (err) {
            setError(err.message);
        }
    };

    const handleSetupComplete = async () => {
        setShowSetupWizard(false);
        await fetchData();
        // Auto-start OAuth after setup
        handleConnect('google');
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-400"></div>
            </div>
        );
    }

    const isGoogleConfigured = oauthStatus?.google?.configured;

    return (
        <div className="space-y-6">
            {/* Setup Wizard Modal */}
            {showSetupWizard && (
                <GoogleSetupWizard
                    onComplete={handleSetupComplete}
                    onClose={() => setShowSetupWizard(false)}
                />
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">📅 Calendar Settings</h2>
                    <p className="text-surface-300 mt-1">
                        Connect your calendar to sync events and find free time
                    </p>
                </div>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-300">
                    {error}
                    <button
                        onClick={() => setError(null)}
                        className="ml-2 text-red-400 hover:text-red-200"
                    >
                        ✕
                    </button>
                </div>
            )}

            {/* Setup Prompt (if not configured) */}
            {!isGoogleConfigured && (
                <section className="glass rounded-xl p-6 border border-primary-500/30">
                    <div className="flex items-start gap-4">
                        <span className="text-4xl">🔐</span>
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-white">Set Up Google Calendar Integration</h3>
                            <p className="text-surface-300 mt-1">
                                To connect your Google Calendar, you need to set up OAuth credentials first.
                                This is a one-time setup that takes about 5 minutes.
                            </p>
                            <button
                                onClick={() => setShowSetupWizard(true)}
                                className="mt-4 px-6 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
                            >
                                Start Setup →
                            </button>
                        </div>
                    </div>
                </section>
            )}

            {/* Connected Calendars */}
            <section className="glass rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Connected Calendars</h3>

                {connections.length === 0 ? (
                    <p className="text-surface-400">No calendars connected yet.</p>
                ) : (
                    <div className="space-y-3">
                        {connections.map(conn => (
                            <div
                                key={conn.id}
                                className="flex items-center justify-between bg-surface-800/50 rounded-lg p-4"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="text-2xl">📅</span>
                                    <div>
                                        <p className="font-medium text-white">{conn.email}</p>
                                        <p className="text-sm text-surface-400">
                                            Google Calendar
                                            {conn.last_sync && (
                                                <> • Last synced: {new Date(conn.last_sync).toLocaleString()}</>
                                            )}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={`px-2 py-1 rounded text-xs ${conn.status === 'connected'
                                        ? 'bg-green-500/20 text-green-400'
                                        : conn.status === 'expired'
                                            ? 'bg-yellow-500/20 text-yellow-400'
                                            : 'bg-red-500/20 text-red-400'
                                        }`}>
                                        {conn.status}
                                    </span>
                                    <button
                                        onClick={() => handleSync(conn.id)}
                                        disabled={syncing[conn.id]}
                                        className="px-3 py-1.5 text-sm bg-primary-500/20 text-primary-400 
                                                   rounded-lg hover:bg-primary-500/30 transition-colors
                                                   disabled:opacity-50"
                                    >
                                        {syncing[conn.id] ? 'Syncing...' : 'Sync Now'}
                                    </button>
                                    <button
                                        onClick={() => handleDisconnect(conn.id)}
                                        className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 transition-colors"
                                    >
                                        Disconnect
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Add Calendar Button */}
                {isGoogleConfigured && (
                    <div className="mt-4 pt-4 border-t border-surface-700">
                        <p className="text-sm text-surface-400 mb-3">Add a calendar:</p>
                        <div className="flex gap-2">
                            {PROVIDERS.map(provider => (
                                <button
                                    key={provider.id}
                                    onClick={() => handleConnect(provider.id)}
                                    disabled={connecting}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-lg 
                                               ${provider.color} text-white hover:opacity-90 transition-opacity
                                               disabled:opacity-50`}
                                >
                                    <span>{provider.icon}</span>
                                    {connecting ? 'Connecting...' : `Connect ${provider.name}`}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </section>

            {/* Sync Preferences */}
            {preferences && (
                <section className="glass rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Sync Preferences</h3>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-white">Auto-sync enabled</p>
                                <p className="text-sm text-surface-400">Automatically sync calendars periodically</p>
                            </div>
                            <button
                                onClick={() => handlePreferenceChange('auto_sync_enabled', !preferences.auto_sync_enabled)}
                                className={`w-12 h-6 rounded-full transition-colors ${preferences.auto_sync_enabled ? 'bg-primary-500' : 'bg-surface-600'
                                    }`}
                            >
                                <div className={`w-5 h-5 rounded-full bg-white transform transition-transform ${preferences.auto_sync_enabled ? 'translate-x-6' : 'translate-x-0.5'
                                    }`} />
                            </button>
                        </div>

                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-white">Export items with due dates</p>
                                <p className="text-sm text-surface-400">Create calendar events for tasks with deadlines</p>
                            </div>
                            <button
                                onClick={() => handlePreferenceChange('export_items_with_due_date', !preferences.export_items_with_due_date)}
                                className={`w-12 h-6 rounded-full transition-colors ${preferences.export_items_with_due_date ? 'bg-primary-500' : 'bg-surface-600'
                                    }`}
                            >
                                <div className={`w-5 h-5 rounded-full bg-white transform transition-transform ${preferences.export_items_with_due_date ? 'translate-x-6' : 'translate-x-0.5'
                                    }`} />
                            </button>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-white text-sm">Working Hours Start</label>
                                <input
                                    type="time"
                                    value={preferences.working_hours_start}
                                    onChange={(e) => handlePreferenceChange('working_hours_start', e.target.value)}
                                    className="mt-1 w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-white"
                                />
                            </div>
                            <div>
                                <label className="text-white text-sm">Working Hours End</label>
                                <input
                                    type="time"
                                    value={preferences.working_hours_end}
                                    onChange={(e) => handlePreferenceChange('working_hours_end', e.target.value)}
                                    className="mt-1 w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-white"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-white text-sm">Minimum free block (minutes)</label>
                            <input
                                type="number"
                                value={preferences.min_free_block_minutes}
                                onChange={(e) => handlePreferenceChange('min_free_block_minutes', parseInt(e.target.value))}
                                min="15"
                                max="240"
                                className="mt-1 w-32 bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-white"
                            />
                        </div>
                    </div>
                </section>
            )}

            {/* Sync History */}
            {connections.length > 0 && (
                <section className="glass rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Sync History</h3>

                    {connections.map(conn => (
                        <div key={conn.id} className="mb-4 last:mb-0">
                            <p className="text-sm text-surface-400 mb-2">{conn.email}</p>
                            {(syncLogs[conn.id] || []).length === 0 ? (
                                <p className="text-surface-500 text-sm">No sync history yet</p>
                            ) : (
                                <div className="space-y-2">
                                    {(syncLogs[conn.id] || []).map(log => (
                                        <div
                                            key={log.id}
                                            className="flex items-center justify-between text-sm bg-surface-800/30 rounded px-3 py-2"
                                        >
                                            <div className="flex items-center gap-2">
                                                <span className={`w-2 h-2 rounded-full ${log.status === 'success' ? 'bg-green-400' :
                                                    log.status === 'partial' ? 'bg-yellow-400' : 'bg-red-400'
                                                    }`} />
                                                <span className="text-surface-300">{log.direction}</span>
                                            </div>
                                            <div className="text-surface-400">
                                                {log.imported_count > 0 && <span className="mr-2">↓{log.imported_count}</span>}
                                                {log.exported_count > 0 && <span className="mr-2">↑{log.exported_count}</span>}
                                                {log.updated_count > 0 && <span className="mr-2">⟳{log.updated_count}</span>}
                                                <span>{new Date(log.started_at).toLocaleString()}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </section>
            )}

            {/* Update Credentials (if already configured) */}
            {isGoogleConfigured && (
                <section className="glass rounded-xl p-6">
                    <details>
                        <summary className="text-surface-400 cursor-pointer hover:text-white">
                            Advanced: Update OAuth Credentials
                        </summary>
                        <div className="mt-4 pt-4 border-t border-surface-700">
                            <p className="text-sm text-surface-400 mb-3">
                                If you need to update your Google OAuth credentials, click below.
                                This won't affect existing connections.
                            </p>
                            <button
                                onClick={() => setShowSetupWizard(true)}
                                className="px-4 py-2 text-sm bg-surface-700 hover:bg-surface-600 text-white rounded-lg transition-colors"
                            >
                                Update Credentials
                            </button>
                        </div>
                    </details>
                </section>
            )}

            {/* Push Notifications Section */}
            <section className="mt-8">
                <NotificationSettings />
            </section>
        </div>
    );
}
