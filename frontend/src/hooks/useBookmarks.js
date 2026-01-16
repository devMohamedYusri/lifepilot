/**
 * useBookmarks - Hook for managing bookmarks
 */
import { useState, useCallback } from 'react';
import { bookmarksApi } from '../api/client';
import useAsync from './useAsync';

export default function useBookmarks(initialFilters = {}) {
    const [filters, setFilters] = useState(initialFilters);
    const [localBookmarks, setLocalBookmarks] = useState([]);

    const fetchBookmarks = useCallback(async () => {
        const data = await bookmarksApi.list(filters);
        setLocalBookmarks(data);
        return data;
    }, [JSON.stringify(filters)]);

    const {
        execute: refresh,
        status,
        error,
        isLoading
    } = useAsync(fetchBookmarks, true);

    const createBookmark = async (url, source, notes) => {
        try {
            const newBookmark = await bookmarksApi.create(url, source, notes);
            setLocalBookmarks(prev => [newBookmark, ...prev]);
            return newBookmark;
        } catch (err) {
            console.error(err);
            throw err;
        }
    };

    const updateBookmark = async (id, data) => {
        setLocalBookmarks(prev => prev.map(b => b.id === id ? { ...b, ...data } : b));
        try {
            const updated = await bookmarksApi.update(id, data);
            setLocalBookmarks(prev => prev.map(b => b.id === id ? updated : b));
            return updated;
        } catch (err) {
            refresh();
            throw err;
        }
    };

    const deleteBookmark = async (id) => {
        setLocalBookmarks(prev => prev.filter(b => b.id !== id));
        try {
            await bookmarksApi.delete(id);
        } catch (err) {
            refresh();
            throw err;
        }
    };

    const updateFilters = (newFilters) => {
        setFilters(prev => ({ ...prev, ...newFilters }));
    };

    return {
        bookmarks: localBookmarks,
        isLoading,
        error,
        refresh,
        createBookmark,
        updateBookmark,
        deleteBookmark,
        filters,
        updateFilters
    };
}
