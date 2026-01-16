import React, { useState } from 'react';
import AgentChat from './AgentChat';
import { useMobile } from '../hooks/useMobile';

/**
 * FloatingAgent - A floating chat button that opens the agent in a modal/panel
 * Accessible from any view without navigation
 */
const FloatingAgent = () => {
    const [isOpen, setIsOpen] = useState(false);
    const { isMobile } = useMobile();

    return (
        <>
            {/* Floating Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`fixed z-50 bg-gradient-to-r from-blue-600 to-purple-600 text-white 
                    rounded-full shadow-lg hover:shadow-xl transition-all duration-300 
                    hover:scale-110 active:scale-95 group
                    ${isMobile ? 'bottom-20 right-4 w-14 h-14' : 'bottom-6 right-6 w-16 h-16'}`}
                title="AI Assistant"
                aria-label="Open AI Assistant"
            >
                {isOpen ? (
                    <svg className="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                ) : (
                    <>
                        <span className="text-2xl">🤖</span>
                        {/* Notification badge for pending actions */}
                        <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            !
                        </span>
                    </>
                )}
            </button>

            {/* Agent Panel/Modal */}
            {isOpen && (
                <div className={`fixed z-40 bg-white dark:bg-gray-900 shadow-2xl rounded-lg overflow-hidden
                    ${isMobile
                        ? 'inset-x-2 bottom-2 top-2'
                        : 'bottom-24 right-6 w-[420px] h-[600px]'
                    }`}
                    style={{
                        animation: 'slideUp 0.3s ease-out',
                        border: '1px solid rgba(255, 255, 255, 0.1)'
                    }}
                >
                    {/* Close button for mobile */}
                    {isMobile && (
                        <button
                            onClick={() => setIsOpen(false)}
                            className="absolute top-3 right-3 z-10 w-8 h-8 bg-gray-800/50 backdrop-blur-sm rounded-full flex items-center justify-center text-white hover:bg-gray-700"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    )}

                    {/* Agent Chat Component */}
                    <div className="h-full">
                        <AgentChat isFloating={true} onClose={() => setIsOpen(false)} />
                    </div>
                </div>
            )}

            {/* Backdrop for mobile */}
            {isOpen && isMobile && (
                <div
                    className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30"
                    onClick={() => setIsOpen(false)}
                />
            )}

            <style jsx>{`
                @keyframes slideUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `}</style>
        </>
    );
};

export default FloatingAgent;
