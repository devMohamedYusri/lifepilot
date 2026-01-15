import { useState } from 'react';
import { itemsApi } from '../api/client';
import VoiceInput from './VoiceInput';

/**
 * Universal inbox input for capturing any thought, task, or item
 * Supports both text and voice input
 */
export default function InboxInput({ onItemCreated }) {
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!content.trim()) return;

        setLoading(true);
        setError(null);

        try {
            const newItem = await itemsApi.create(content.trim());
            setContent('');
            if (onItemCreated) {
                onItemCreated(newItem);
            }
        } catch (err) {
            setError(err.message || 'Failed to process item');
        } finally {
            setLoading(false);
        }
    };

    // Handle voice transcription - fill the text input
    const handleTranscription = (text) => {
        setContent(prevContent => {
            // If there's existing content, add a space
            if (prevContent.trim()) {
                return prevContent.trim() + ' ' + text;
            }
            return text;
        });
    };

    // Handle voice capture - items created directly from voice
    const handleVoiceItemCreated = (items) => {
        if (onItemCreated && items.length > 0) {
            items.forEach(item => onItemCreated(item));
        }
    };

    return (
        <div className="w-full">
            <form onSubmit={handleSubmit} className="relative">
                <div className="glass rounded-2xl p-1.5 glow-primary">
                    <div className="flex items-center gap-3">
                        {/* Voice Input Button */}
                        <div className="pl-3">
                            <VoiceInput
                                mode="transcribe"
                                onTranscription={handleTranscription}
                                onItemCreated={handleVoiceItemCreated}
                            />
                        </div>

                        <div className="flex-1 relative">
                            <input
                                type="text"
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                placeholder="What's on your mind? Type or speak..."
                                className="w-full px-4 py-4 bg-transparent text-white text-lg 
                         placeholder-surface-200/60 focus:outline-none"
                                disabled={loading}
                                autoFocus
                            />
                            {loading && (
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2 text-primary-400">
                                    <div className="spinner"></div>
                                    <span className="text-sm">Processing...</span>
                                </div>
                            )}
                        </div>
                        <button
                            type="submit"
                            disabled={loading || !content.trim()}
                            className="btn-primary px-6 py-3 text-base font-semibold rounded-xl 
                       flex items-center gap-2 mr-1"
                        >
                            {loading ? (
                                <>
                                    <div className="spinner"></div>
                                    <span>AI Processing</span>
                                </>
                            ) : (
                                <>
                                    <span>Capture</span>
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                            d="M12 4v16m8-8H4" />
                                    </svg>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </form>

            {error && (
                <div className="mt-3 px-4 py-2 bg-red-500/10 border border-red-500/30 
                      rounded-lg text-red-400 text-sm animate-fade-in">
                    ⚠️ {error}
                </div>
            )}

            <p className="mt-3 text-center text-surface-200/60 text-sm">
                💡 Try: "Call mom tomorrow" • "Waiting for John's report" • "Should I take the job offer?"
                <span className="ml-2 text-primary-400/60">🎤 Click mic to use voice</span>
            </p>
        </div>
    );
}
