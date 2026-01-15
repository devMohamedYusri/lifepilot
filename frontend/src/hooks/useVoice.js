/**
 * useVoice - Hook for voice recording in chat
 */
import { useState, useRef, useCallback } from 'react';
import { voiceApi } from '../api/client';

export function useVoice() {
    const [isRecording, setIsRecording] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const streamRef = useRef(null);

    const startRecording = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true }
            });

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
                setIsProcessing(true);

                try {
                    const result = await voiceApi.transcribe(audioBlob);
                    if (result.text) {
                        setTranscript(result.text);
                    }
                } catch (err) {
                    console.error('Transcription failed:', err);
                } finally {
                    setIsProcessing(false);
                }
            };

            mediaRecorderRef.current = mediaRecorder;
            mediaRecorder.start(100);
            setIsRecording(true);

        } catch (err) {
            console.error('Microphone access failed:', err);
        }
    }, []);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current?.state !== 'inactive') {
            mediaRecorderRef.current?.stop();
        }
        streamRef.current?.getTracks().forEach(t => t.stop());
        streamRef.current = null;
        setIsRecording(false);
    }, []);

    const toggleRecording = useCallback(() => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }, [isRecording, startRecording, stopRecording]);

    return {
        isRecording,
        isProcessing,
        transcript,
        setTranscript,
        toggleRecording,
        startRecording,
        stopRecording
    };
}
