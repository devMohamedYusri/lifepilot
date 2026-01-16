/**
 * Focus API
 */
import { request } from './core';

export const focusApi = {
    getToday: () => request('/focus/today'),
};
