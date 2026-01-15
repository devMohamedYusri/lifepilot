/**
 * NotificationSettings - Push notification permission and preferences
 */
import { useState, useEffect, useCallback } from 'react';
import { pushApi } from '../api/client';

export default function NotificationSettings() {
    const [status, setStatus] = useState(null);
    const [preferences, setPreferences] = useState(null);
    const [loading, setLoading] = useState(true);
    const [subscribing, setSubscribing] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    // Check if notifications are supported
    const isSupported = 'Notification' in window && 'serviceWorker' in navigator;
    const permission = isSupported ? Notification.permission : 'unsupported';

    const fetchStatus = useCallback(async () => {
        try {
            const [statusData, prefsData] = await Promise.all([
                pushApi.getStatus(),
                pushApi.getPreferences()
            ]);
            setStatus(statusData);
            setPreferences(prefsData);
        } catch (err) {
            console.error('Failed to load push status:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStatus();
    }, [fetchStatus]);

    // Request notification permission and subscribe
    const handleEnableNotifications = async () => {
        if (!isSupported) {
            setError('Push notifications are not supported in this browser');
            return;
        }

        setSubscribing(true);
        setError(null);

        try {
            // Request permission
            const result = await Notification.requestPermission();

            if (result !== 'granted') {
                setError('Notification permission denied');
                setSubscribing(false);
                return;
            }

            // Get VAPID key
            let vapidKey;
            try {
                const keyResponse = await pushApi.getVapidKey();
                vapidKey = keyResponse.publicKey;
            } catch (err) {
                setError('Push notifications not configured on server. VAPID keys required.');
                setSubscribing(false);
                return;
            }

            // Get service worker registration
            const registration = await navigator.serviceWorker.ready;

            // Subscribe to push
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidKey)
            });

            // Send subscription to server
            await pushApi.subscribe(subscription, getDeviceName());

            setSuccess('Notifications enabled!');
            await fetchStatus();

        } catch (err) {
            console.error('Subscription failed:', err);
            setError(err.message || 'Failed to enable notifications');
        } finally {
            setSubscribing(false);
        }
    };

    // Disable notifications
    const handleDisableNotifications = async () => {
        setSubscribing(true);
        setError(null);

        try {
            const registration = await navigator.serviceWorker.ready;
            const subscription = await registration.pushManager.getSubscription();

            if (subscription) {
                await pushApi.unsubscribe(subscription.endpoint);
                await subscription.unsubscribe();
            }

            setSuccess('Notifications disabled');
            await fetchStatus();

        } catch (err) {
            setError(err.message || 'Failed to disable notifications');
        } finally {
            setSubscribing(false);
        }
    };

    // Update preference
    const handlePreferenceChange = async (key, value) => {
        try {
            await pushApi.updatePreferences({ [key]: value });
            setPreferences(prev => ({ ...prev, [key]: value }));
        } catch (err) {
            setError('Failed to update preference');
        }
    };

    // Send test notification
    const handleTestNotification = async () => {
        try {
            await pushApi.sendTest('Test from LifePilot', 'Push notifications are working! 🚀');
            setSuccess('Test notification sent');
        } catch (err) {
            setError(err.message || 'Failed to send test notification');
        }
    };

    if (loading) {
        return (
            <div className="glass rounded-xl p-6">
                <div className="flex items-center justify-center gap-3">
                    <div className="spinner"></div>
                    <span>Loading notification settings...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="glass rounded-xl p-6">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    🔔 Push Notifications
                </h3>

                {/* Status */}
                <div className="mb-6 p-4 bg-surface-800/50 rounded-lg">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="font-medium text-white">
                                {permission === 'granted' ? '✅ Enabled' :
                                    permission === 'denied' ? '🚫 Blocked' :
                                        permission === 'unsupported' ? '❌ Not Supported' :
                                            '⏸️ Not Enabled'}
                            </p>
                            <p className="text-sm text-surface-300">
                                {permission === 'granted'
                                    ? `${status?.subscription_count || 0} device(s) subscribed`
                                    : permission === 'denied'
                                        ? 'Enable in browser settings'
                                        : 'Get notified about tasks and reminders'}
                            </p>
                        </div>

                        {permission !== 'unsupported' && (
                            <button
                                onClick={permission === 'granted' ? handleDisableNotifications : handleEnableNotifications}
                                disabled={subscribing}
                                className={`px-4 py-2 rounded-lg font-medium transition-all ${permission === 'granted'
                                        ? 'bg-surface-700 hover:bg-surface-600 text-white'
                                        : 'bg-primary-500 hover:bg-primary-600 text-white'
                                    } disabled:opacity-50`}
                            >
                                {subscribing ? 'Processing...' : permission === 'granted' ? 'Disable' : 'Enable'}
                            </button>
                        )}
                    </div>
                </div>

                {/* Messages */}
                {error && (
                    <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="mb-4 p-3 bg-green-500/20 border border-green-500/30 rounded-lg text-green-300 text-sm">
                        {success}
                    </div>
                )}

                {/* Preferences */}
                {preferences && permission === 'granted' && (
                    <div className="space-y-4">
                        <h4 className="font-medium text-surface-200">Notification Types</h4>

                        <label className="flex items-center justify-between p-3 bg-surface-800/30 rounded-lg">
                            <div>
                                <p className="text-white">Task Reminders</p>
                                <p className="text-sm text-surface-400">Get notified when tasks are due</p>
                            </div>
                            <ToggleSwitch
                                checked={preferences.task_reminders}
                                onChange={(v) => handlePreferenceChange('task_reminders', v)}
                            />
                        </label>

                        <label className="flex items-center justify-between p-3 bg-surface-800/30 rounded-lg">
                            <div>
                                <p className="text-white">Follow-up Reminders</p>
                                <p className="text-sm text-surface-400">Reminders for waiting items</p>
                            </div>
                            <ToggleSwitch
                                checked={preferences.followup_reminders}
                                onChange={(v) => handlePreferenceChange('followup_reminders', v)}
                            />
                        </label>

                        <label className="flex items-center justify-between p-3 bg-surface-800/30 rounded-lg">
                            <div>
                                <p className="text-white">Contact Reminders</p>
                                <p className="text-sm text-surface-400">Reach out to people you haven't contacted</p>
                            </div>
                            <ToggleSwitch
                                checked={preferences.contact_reminders}
                                onChange={(v) => handlePreferenceChange('contact_reminders', v)}
                            />
                        </label>

                        <label className="flex items-center justify-between p-3 bg-surface-800/30 rounded-lg">
                            <div>
                                <p className="text-white">Daily Summary</p>
                                <p className="text-sm text-surface-400">Morning summary of your day</p>
                            </div>
                            <ToggleSwitch
                                checked={preferences.daily_summary}
                                onChange={(v) => handlePreferenceChange('daily_summary', v)}
                            />
                        </label>

                        {/* Quiet Hours */}
                        <div className="pt-4 border-t border-surface-700">
                            <h4 className="font-medium text-surface-200 mb-3">Quiet Hours</h4>
                            <div className="flex items-center gap-4">
                                <div>
                                    <label className="text-sm text-surface-400">Start</label>
                                    <input
                                        type="time"
                                        value={preferences.quiet_hours_start || '22:00'}
                                        onChange={(e) => handlePreferenceChange('quiet_hours_start', e.target.value)}
                                        className="block mt-1 px-3 py-2 bg-surface-800 border border-surface-600 
                                                   rounded-lg text-white"
                                    />
                                </div>
                                <div>
                                    <label className="text-sm text-surface-400">End</label>
                                    <input
                                        type="time"
                                        value={preferences.quiet_hours_end || '08:00'}
                                        onChange={(e) => handlePreferenceChange('quiet_hours_end', e.target.value)}
                                        className="block mt-1 px-3 py-2 bg-surface-800 border border-surface-600 
                                                   rounded-lg text-white"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Test Button */}
                        <div className="pt-4">
                            <button
                                onClick={handleTestNotification}
                                className="px-4 py-2 bg-surface-700 hover:bg-surface-600 
                                         text-white rounded-lg transition-colors"
                            >
                                Send Test Notification
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// Toggle Switch Component
function ToggleSwitch({ checked, onChange }) {
    return (
        <button
            role="switch"
            aria-checked={checked}
            onClick={() => onChange(!checked)}
            className={`relative w-11 h-6 rounded-full transition-colors ${checked ? 'bg-primary-500' : 'bg-surface-600'
                }`}
        >
            <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full 
                           transition-transform ${checked ? 'translate-x-5' : ''}`}
            />
        </button>
    );
}

// Helper: Convert VAPID key to Uint8Array
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Helper: Get device name
function getDeviceName() {
    const ua = navigator.userAgent;
    if (/iPhone/i.test(ua)) return 'iPhone';
    if (/iPad/i.test(ua)) return 'iPad';
    if (/Android/i.test(ua)) return 'Android';
    if (/Windows/i.test(ua)) return 'Windows';
    if (/Mac/i.test(ua)) return 'Mac';
    if (/Linux/i.test(ua)) return 'Linux';
    return 'Unknown Device';
}
