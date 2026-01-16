/**
 * useMobile - Hook for detecting mobile viewport and PWA install state
 */
import { useState, useEffect, useCallback } from 'react';

const MOBILE_BREAKPOINT = 1024;

export function useMobile() {
    const [isMobile, setIsMobile] = useState(
        typeof window !== 'undefined' ? window.innerWidth < MOBILE_BREAKPOINT : false
    );
    const [isStandalone, setIsStandalone] = useState(false);
    const [installPrompt, setInstallPrompt] = useState(null);
    const [isInstallable, setIsInstallable] = useState(false);

    useEffect(() => {
        // Check if running as installed PWA
        const checkStandalone = () => {
            const standalone =
                window.matchMedia('(display-mode: standalone)').matches ||
                window.navigator.standalone ||
                document.referrer.includes('android-app://');
            setIsStandalone(standalone);
        };

        checkStandalone();

        // Handle resize
        const handleResize = () => {
            setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
        };

        // Handle beforeinstallprompt
        const handleInstallPrompt = (event) => {
            event.preventDefault();
            setInstallPrompt(event);
            setIsInstallable(true);
        };

        // Handle appinstalled
        const handleAppInstalled = () => {
            setInstallPrompt(null);
            setIsInstallable(false);
            setIsStandalone(true);
        };

        window.addEventListener('resize', handleResize);
        window.addEventListener('beforeinstallprompt', handleInstallPrompt);
        window.addEventListener('appinstalled', handleAppInstalled);

        return () => {
            window.removeEventListener('resize', handleResize);
            window.removeEventListener('beforeinstallprompt', handleInstallPrompt);
            window.removeEventListener('appinstalled', handleAppInstalled);
        };
    }, []);

    // Trigger install prompt
    const promptInstall = useCallback(async () => {
        if (!installPrompt) return false;

        try {
            installPrompt.prompt();
            const result = await installPrompt.userChoice;

            if (result.outcome === 'accepted') {
                setInstallPrompt(null);
                setIsInstallable(false);
                return true;
            }
            return false;
        } catch (error) {
            console.error('Install prompt failed:', error);
            return false;
        }
    }, [installPrompt]);

    return {
        isMobile,
        isStandalone,
        isInstallable,
        promptInstall
    };
}

export default useMobile;
