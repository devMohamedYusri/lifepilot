/**
 * useAsync - Generic hook for async data fetching
 */
import { useState, useCallback, useEffect } from 'react';

/**
 * Hook for managing async operations with loading/error states
 * 
 * @param {Function} asyncFn - Async function to call
 * @param {boolean} immediate - Whether to call immediately on mount
 * @returns {Object} { data, loading, error, execute, reset }
 */
export default function useAsync(asyncFn, immediate = false) {
    const [state, setState] = useState({
        data: null,
        loading: immediate,
        error: null
    });

    const execute = useCallback(async (...args) => {
        setState(prev => ({ ...prev, loading: true, error: null }));

        try {
            const result = await asyncFn(...args);
            setState({ data: result, loading: false, error: null });
            return result;
        } catch (error) {
            const errorMessage = error.message || 'An error occurred';
            setState(prev => ({ ...prev, loading: false, error: errorMessage }));
            throw error;
        }
    }, [asyncFn]);

    const reset = useCallback(() => {
        setState({ data: null, loading: false, error: null });
    }, []);

    useEffect(() => {
        if (immediate) {
            execute();
        }
    }, []);  // eslint-disable-line react-hooks/exhaustive-deps

    return {
        ...state,
        execute,
        reset
    };
}
