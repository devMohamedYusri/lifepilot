/**
 * useAsync - Generic hook for async operations with state
 */
import { useState, useCallback, useEffect } from 'react';

export default function useAsync(asyncFunction, immediate = true) {
    const [status, setStatus] = useState('idle');
    const [value, setValue] = useState(null);
    const [error, setError] = useState(null);

    // The execute function wraps asyncFunction and handles setting state
    // useCallback ensures it doesn't change on every render unless asyncFunction changes
    const execute = useCallback(
        async (...args) => {
            setStatus('pending');
            setError(null);

            try {
                const response = await asyncFunction(...args);
                setValue(response);
                setStatus('success');
                return response;
            } catch (error) {
                setError(error);
                setStatus('error');
                // Log error for debugging but don't crash app
                console.error('Async operation failed:', error);
                throw error;
            }
        },
        [asyncFunction]
    );

    // Call execute immediately if requested
    useEffect(() => {
        if (immediate) {
            execute();
        }
    }, [execute, immediate]);

    return {
        execute,
        status,
        value,
        error,
        isLoading: status === 'pending',
        isSuccess: status === 'success',
        isError: status === 'error',
        reset: () => {
            setStatus('idle');
            setValue(null);
            setError(null);
        }
    };
}
