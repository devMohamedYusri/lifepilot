/**
 * useContacts - Hook for managing contacts (CRM)
 */
import { useState, useCallback } from 'react';
import { contactsApi } from '../api/client';
import useAsync from './useAsync';

export default function useContacts(params = {}) {
    const [localContacts, setLocalContacts] = useState([]);

    // Fetch contacts wrap
    const fetchContacts = useCallback(async () => {
        const data = await contactsApi.list(params);
        setLocalContacts(data);
        return data;
    }, [JSON.stringify(params)]);

    const {
        execute: refresh,
        status,
        value: contacts,
        error,
        isLoading
    } = useAsync(fetchContacts, true);

    const createContact = async (data) => {
        try {
            const newContact = await contactsApi.create(data);
            setLocalContacts(prev => [...prev, newContact]);
            return newContact;
        } catch (err) {
            console.error(err);
            throw err;
        }
    };

    const updateContact = async (id, data) => {
        // Optimistic
        setLocalContacts(prev => prev.map(c => c.id === id ? { ...c, ...data } : c));
        try {
            const updated = await contactsApi.update(id, data);
            setLocalContacts(prev => prev.map(c => c.id === id ? updated : c));
            return updated;
        } catch (err) {
            refresh();
            throw err;
        }
    };

    const deleteContact = async (id) => {
        setLocalContacts(prev => prev.filter(c => c.id !== id));
        try {
            await contactsApi.delete(id);
        } catch (err) {
            refresh();
            throw err;
        }
    };

    return {
        contacts: localContacts,
        isLoading,
        error,
        refresh,
        createContact,
        updateContact,
        deleteContact
    };
}
