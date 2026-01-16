/**
 * useDecisions - Hook for managing decisions
 */
import { useState, useCallback } from 'react';
import { decisionsApi } from '../api/client';
import useAsync from './useAsync';

export default function useDecisions(initialFilters = {}) {
    const [filters, setFilters] = useState(initialFilters);
    const [localDecisions, setLocalDecisions] = useState([]);

    const fetchDecisions = useCallback(async () => {
        const data = await decisionsApi.list(filters);
        setLocalDecisions(data);
        return data;
    }, [JSON.stringify(filters)]);

    const {
        execute: refresh,
        error,
        isLoading
    } = useAsync(fetchDecisions, true);

    const expandDecision = async (itemId, data) => {
        try {
            const newDecision = await decisionsApi.expand(itemId, data);
            setLocalDecisions(prev => [...prev, newDecision]);
            return newDecision;
        } catch (err) {
            console.error(err);
            throw err;
        }
    };

    const updateDecision = async (id, data) => {
        setLocalDecisions(prev => prev.map(d => d.id === id ? { ...d, ...data } : d));
        try {
            const updated = await decisionsApi.update(id, data);
            setLocalDecisions(prev => prev.map(d => d.id === id ? updated : d));
            return updated;
        } catch (err) {
            refresh();
            throw err;
        }
    };

    const recordOutcome = async (id, outcome) => {
        try {
            const updated = await decisionsApi.recordOutcome(id, outcome);
            setLocalDecisions(prev => prev.map(d => d.id === id ? updated : d));
            return updated;
        } catch (err) {
            refresh();
            throw err;
        }
    };

    return {
        decisions: localDecisions,
        isLoading,
        error,
        refresh,
        expandDecision,
        updateDecision,
        recordOutcome,
        filters,
        setFilters
    };
}
