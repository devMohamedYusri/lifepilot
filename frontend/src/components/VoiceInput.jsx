/**
 * VoiceInput - Voice recording and transcription component
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import { voiceApi } from '../api/client';

// Recording states
const STATE = {
    IDLE: 'idle',
    REQUESTING: 'requesting',
    RECORDING: 'recording',
    PROCESSING: 'processing',
    REVIEW: 'review',
    SUCCESS: 'success',
    ERROR: 'error'
};

export default function VoiceInput({ onTranscription, onItemCreated, mode = 'transcribe' }) {
    const [state, setState] = useState(STATE.IDLE);
    const [error, setError] = useState(null);
    const [duration, setDuration] = useState(0);
    const [audioLevel, setAudioLevel] = useState(0);
    const [transcription, setTranscription] = useState('');
    const [createdItems, setCreatedItems] = useState([]);

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const streamRef = useRef(null);
    const analyserRef = useRef(null);
    const animationRef = useRef(null);
    const durationTimerRef = useRef(null);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopRecording();
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
            if (durationTimerRef.current) clearInterval(durationTimerRef.current);
        };
    }, []);

    // Audio level visualization
    const updateAudioLevel = useCallback(() => {
        if (!analyserRef.current) return;

        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteFrequencyData(dataArray);

        // Calculate average level
        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        setAudioLevel(average / 255);

        if (state === STATE.RECORDING) {
            animationRef.current = requestAnimationFrame(updateAudioLevel);
        }
    }, [state]);

    const startRecording = async () => {
        setError(null);
        setState(STATE.REQUESTING);

        try {
            // Request microphone permission
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            });

            streamRef.current = stream;

            // Set up audio analyser for level visualization
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaStreamSource(stream);
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);
            analyserRef.current = analyser;

            // Create MediaRecorder
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await processAudio(audioBlob);
            };

            mediaRecorderRef.current = mediaRecorder;
            mediaRecorder.start(100); // Collect data every 100ms

            setState(STATE.RECORDING);
            setDuration(0);

            // Start duration timer
            durationTimerRef.current = setInterval(() => {
                setDuration(d => d + 1);
            }, 1000);

            // Start audio level visualization
            updateAudioLevel();

        } catch (err) {
            console.error('Microphone error:', err);
            setState(STATE.ERROR);

            if (err.name === 'NotAllowedError') {
                setError('Microphone access denied. Please allow microphone access in your browser settings.');
            } else if (err.name === 'NotFoundError') {
                setError('No microphone found. Please connect a microphone.');
            } else {
                setError(err.message || 'Failed to access microphone');
            }
        }
    };

    const stopRecording = () => {
        if (durationTimerRef.current) {
            clearInterval(durationTimerRef.current);
            durationTimerRef.current = null;
        }

        if (animationRef.current) {
            cancelAnimationFrame(animationRef.current);
            animationRef.current = null;
        }

        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }

        setAudioLevel(0);
    };

    const cancelRecording = () => {
        stopRecording();
        audioChunksRef.current = [];
        setState(STATE.IDLE);
        setDuration(0);
    };

    const processAudio = async (audioBlob) => {
        setState(STATE.PROCESSING);

        try {
            if (mode === 'capture') {
                // Transcribe and create items
                const result = await voiceApi.capture(audioBlob);

                if (result.items && result.items.length > 0) {
                    setCreatedItems(result.items);
                    onItemCreated?.(result.items);
                    setState(STATE.SUCCESS);

                    // Auto-reset after showing success
                    setTimeout(() => {
                        setState(STATE.IDLE);
                        setCreatedItems([]);
                    }, 2000);
                } else if (result.transcription) {
                    setTranscription(result.transcription);
                    setState(STATE.REVIEW);
                } else {
                    setError('No speech detected. Try speaking closer to the microphone.');
                    setState(STATE.ERROR);
                }
            } else {
                // Just transcribe
                const result = await voiceApi.transcribe(audioBlob);

                if (result.text) {
                    setTranscription(result.text);
                    onTranscription?.(result.text);
                    setState(STATE.REVIEW);
                } else {
                    setError('No speech detected. Try speaking closer to the microphone.');
                    setState(STATE.ERROR);
                }
            }
        } catch (err) {
            console.error('Processing error:', err);
            setError(err.message || 'Failed to process audio');
            setState(STATE.ERROR);
        }
    };

    const handleButtonClick = () => {
        if (state === STATE.IDLE || state === STATE.ERROR) {
            startRecording();
        } else if (state === STATE.RECORDING) {
            stopRecording();
        }
    };

    const resetToIdle = () => {
        setState(STATE.IDLE);
        setError(null);
        setTranscription('');
        setCreatedItems([]);
        setDuration(0);
    };

    const formatDuration = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="relative inline-flex items-center">
            {/* Main Button */}
            <button
                onClick={handleButtonClick}
                disabled={state === STATE.PROCESSING || state === STATE.REQUESTING}
                className={`
                    relative w-10 h-10 rounded-full transition-all duration-200
                    flex items-center justify-center
                    ${state === STATE.RECORDING
                        ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                        : state === STATE.PROCESSING || state === STATE.REQUESTING
                            ? 'bg-surface-600 cursor-wait'
                            : state === STATE.SUCCESS
                                ? 'bg-green-500'
                                : state === STATE.ERROR
                                    ? 'bg-red-500/50 hover:bg-red-500'
                                    : 'bg-surface-700 hover:bg-surface-600'
                    }
                `}
                title={state === STATE.IDLE ? 'Start voice recording (V)' :
                    state === STATE.RECORDING ? 'Stop recording' : 'Voice input'}
            >
                {state === STATE.PROCESSING || state === STATE.REQUESTING ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : state === STATE.SUCCESS ? (
                    <span className="text-lg">✓</span>
                ) : state === STATE.RECORDING ? (
                    <span className="text-lg">⏹</span>
                ) : (
                    <span className="text-lg">🎤</span>
                )}

                {/* Audio Level Ring */}
                {state === STATE.RECORDING && (
                    <div
                        className="absolute inset-0 rounded-full border-2 border-red-300"
                        style={{
                            transform: `scale(${1 + audioLevel * 0.3})`,
                            opacity: 0.5 + audioLevel * 0.5
                        }}
                    />
                )}
            </button>

            {/* Recording Indicator */}
            {state === STATE.RECORDING && (
                <div className="ml-2 flex items-center gap-2 text-sm text-red-400">
                    <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                    <span>{formatDuration(duration)}</span>
                    <button
                        onClick={cancelRecording}
                        className="text-surface-400 hover:text-white text-xs ml-1"
                    >
                        Cancel
                    </button>
                </div>
            )}

            {/* Error Message */}
            {state === STATE.ERROR && error && (
                <div className="absolute top-full left-0 mt-2 p-3 bg-surface-800 border border-red-500/30 
                               rounded-lg text-sm text-red-300 max-w-xs z-10">
                    {error}
                    <button
                        onClick={resetToIdle}
                        className="ml-2 text-red-400 hover:text-red-200"
                    >
                        Dismiss
                    </button>
                </div>
            )}

            {/* Review Overlay */}
            {state === STATE.REVIEW && (
                <div className="absolute top-full left-0 mt-2 p-4 bg-surface-800 border border-surface-600 
                               rounded-lg shadow-xl min-w-[300px] max-w-md z-20">
                    <p className="text-sm text-surface-400 mb-2">Transcription:</p>
                    <p className="text-white mb-3">{transcription}</p>
                    <div className="flex gap-2">
                        <button
                            onClick={() => {
                                onTranscription?.(transcription);
                                resetToIdle();
                            }}
                            className="px-3 py-1.5 text-sm bg-primary-500 hover:bg-primary-600 
                                       text-white rounded-lg transition-colors"
                        >
                            Use Text
                        </button>
                        <button
                            onClick={resetToIdle}
                            className="px-3 py-1.5 text-sm text-surface-400 hover:text-white transition-colors"
                        >
                            Discard
                        </button>
                    </div>
                </div>
            )}

            {/* Success Message */}
            {state === STATE.SUCCESS && createdItems.length > 0 && (
                <div className="ml-2 text-sm text-green-400">
                    Created {createdItems.length} item{createdItems.length > 1 ? 's' : ''}!
                </div>
            )}
        </div>
    );
}


/**
 * VoiceInputOverlay - Full screen recording overlay for mobile
 */
export function VoiceInputOverlay({ isOpen, onClose, onItemCreated }) {
    const [state, setState] = useState('idle');
    const [duration, setDuration] = useState(0);
    const [transcription, setTranscription] = useState('');
    const [error, setError] = useState(null);

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const streamRef = useRef(null);
    const timerRef = useRef(null);

    useEffect(() => {
        if (isOpen) {
            startRecording();
        }
        return () => stopRecording();
    }, [isOpen]);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunksRef.current.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await processAudio(audioBlob);
            };

            mediaRecorderRef.current = mediaRecorder;
            mediaRecorder.start(100);
            setState('recording');

            timerRef.current = setInterval(() => setDuration(d => d + 1), 1000);

        } catch (err) {
            setError(err.message);
            setState('error');
        }
    };

    const stopRecording = () => {
        if (timerRef.current) clearInterval(timerRef.current);
        if (mediaRecorderRef.current?.state !== 'inactive') {
            mediaRecorderRef.current?.stop();
        }
        streamRef.current?.getTracks().forEach(t => t.stop());
    };

    const processAudio = async (audioBlob) => {
        setState('processing');
        try {
            const result = await voiceApi.capture(audioBlob);
            if (result.items?.length > 0) {
                onItemCreated?.(result.items);
                onClose();
            } else {
                setTranscription(result.transcription || 'No speech detected');
                setState('review');
            }
        } catch (err) {
            setError(err.message);
            setState('error');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-surface-950/95 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="text-center">
                {/* Recording visualization */}
                <div className={`w-32 h-32 rounded-full mx-auto mb-8 flex items-center justify-center
                               ${state === 'recording' ? 'bg-red-500 animate-pulse' : 'bg-surface-800'}`}>
                    {state === 'processing' ? (
                        <div className="w-12 h-12 border-4 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        <span className="text-5xl">🎤</span>
                    )}
                </div>

                {/* Duration */}
                {state === 'recording' && (
                    <div className="text-4xl font-mono text-white mb-8">
                        {Math.floor(duration / 60)}:{(duration % 60).toString().padStart(2, '0')}
                    </div>
                )}

                {/* Instructions/Status */}
                <p className="text-lg text-surface-300 mb-8">
                    {state === 'recording' && 'Listening...'}
                    {state === 'processing' && 'Processing...'}
                    {state === 'error' && error}
                    {state === 'review' && transcription}
                </p>

                {/* Controls */}
                <div className="flex gap-4 justify-center">
                    {state === 'recording' && (
                        <button
                            onClick={stopRecording}
                            className="px-8 py-3 bg-red-500 hover:bg-red-600 text-white rounded-full text-lg"
                        >
                            Done
                        </button>
                    )}
                    <button
                        onClick={onClose}
                        className="px-8 py-3 bg-surface-700 hover:bg-surface-600 text-white rounded-full text-lg"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
