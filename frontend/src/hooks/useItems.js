/**
 * useItems - Hook for managing tasks and items
 */
import { useState, useCallback } from 'react';
import { itemsApi } from '../api/client';
import useAsync from './useAsync';

export default function useItems(initialFilters = {}) {
    const [filters, setFilters] = useState(initialFilters);
    const [localItems, setLocalItems] = useState([]);

    // Fetch list wrapper
    const fetchList = useCallback(async () => {
        const data = await itemsApi.list(filters);
        // If API returns array directly, use it. If nested in 'items', use that.
        const list = Array.isArray(data) ? data : (data.items || []);
        setLocalItems(list);
        return list;
    }, [filters]);

    const {
        execute: refresh,
        status,
        value: items,
        error,
        isLoading
    } = useAsync(fetchList, true);

    // Create item
    const createItem = async (content) => {
        const validation = validateContent(content);
        if (!validation.isValid) throw new Error(validation.error);

        try {
            const newItem = await itemsApi.create(content);
            setLocalItems(prev => [newItem, ...prev]);
            return newItem;
        } catch (err) {
            console.error('Failed to create item:', err);
            throw err;
        }
    };

    // Update item
    const updateItem = async (id, data) => {
        try {
            // Optimistic update
            setLocalItems(prev => prev.map(item =>
                item.id === id ? { ...item, ...data } : item
            ));

            const updated = await itemsApi.update(id, data);

            // Revert/fix with server data
            setLocalItems(prev => prev.map(item =>
                item.id === id ? updated : item
            ));
            return updated;
        } catch (err) {
            // Revert optimistic update on failure (requires refetching or more complex state)
            refresh();
            throw err;
        }
    };

    // Delete item
    const deleteItem = async (id) => {
        try {
            setLocalItems(prev => prev.filter(item => item.id !== id));
            await itemsApi.delete(id);
        } catch (err) {
            refresh();
            throw err;
        }
    };

    // Helper: Update filters
    const updateFilters = (newFilters) => {
        setFilters(prev => ({ ...prev, ...newFilters }));
    };

    // Validation
    const validateContent = (content) => {
        if (!content || !content.trim()) return { isValid: false, error: 'Content cannot be empty' };
        if (content.length > 500) return { isValid: false, error: 'Content too long (max 500 chars)' };
        return { isValid: true };
    };

    return {
        items: localItems, // Use local state for immediate feedback
        isLoading,
        error,
        refresh,
        createItem,
        updateItem,
        deleteItem,
        filters,
        updateFilters,
        setFilters
    };
}
