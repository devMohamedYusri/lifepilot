import React, { useState, useEffect, useRef } from 'react';
import { agentApi } from '../api/client';
import { useVoice } from '../hooks/useVoice';

// Simple markdown-like formatting
const formatMessage = (text) => {
    if (!text) return '';

    // Bold: **text**
    let formatted = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Italic: *text*
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Code: `text`
    formatted = formatted.replace(/`(.+?)`/g, '<code class="bg-gray-100 dark:bg-gray-700 px-1 rounded text-sm">$1</code>');
    // Line breaks
    formatted = formatted.replace(/\n/g, '<br/>');

    return formatted;
};

// Conversation starters
const CONVERSATION_STARTERS = [
    { icon: '🎯', text: "What should I focus on today?" },
    { icon: '📋', text: "Show me my overdue items" },
    { icon: '📅', text: "What's on my calendar?" },
    { icon: '👋', text: "Who should I reach out to?" },
    { icon: '⚡', text: "Help me plan my week" }
];

const AgentChat = ({ isFloating = false, onClose = null }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [pendingActions, setPendingActions] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [showHistory, setShowHistory] = useState(false);
    const messagesEndRef = useRef(null);

    // Voice input hook
    const { isRecording, toggleRecording, transcript, setTranscript } = useVoice();

    // Load initial history or status
    useEffect(() => {
        loadConversations();
        loadPendingActions();
    }, []);

    // Update input when voice transcript changes
    useEffect(() => {
        if (transcript) {
            setInput(transcript);
        }
    }, [transcript]);

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const loadConversations = async () => {
        try {
            const convos = await agentApi.listConversations(10);
            setConversations(convos || []);

            if (convos && convos.length > 0) {
                // Load most recent conversation
                const lastSessionId = convos[0].session_id;
                setSessionId(lastSessionId);
                const history = await agentApi.getConversation(lastSessionId);
                if (history && history.messages) {
                    setMessages(history.messages);
                }
            } else {
                // Show welcome for new users
                showWelcome();
            }
        } catch (err) {
            console.error('Failed to load conversations:', err);
            showWelcome();
        }
    };

    const showWelcome = () => {
        setMessages([{
            role: 'assistant',
            content: "👋 Hello! I'm your LifePilot assistant.\\n\\nI can help you manage tasks, track contacts, plan your day, and more. Try asking me something!",
            created_at: new Date().toISOString()
        }]);
        setSuggestions(CONVERSATION_STARTERS.map(s => s.text));
    };

    const loadPendingActions = async () => {
        try {
            const actions = await agentApi.getPendingActions();
            setPendingActions(actions);
        } catch (err) {
            console.error('Failed to load pending actions:', err);
        }
    };

    const startNewChat = () => {
        setSessionId(null);
        setMessages([]);
        showWelcome();
        setShowHistory(false);
    };

    const switchConversation = async (convSessionId) => {
        try {
            const history = await agentApi.getConversation(convSessionId);
            if (history && history.messages) {
                setSessionId(convSessionId);
                setMessages(history.messages);
                setSuggestions([]);
            }
            setShowHistory(false);
        } catch (err) {
            console.error('Failed to load conversation:', err);
        }
    };

    const handleSend = async (e, quickReply = null) => {
        e?.preventDefault();
        const userMsg = quickReply || input.trim();
        if (!userMsg || loading) return;

        setInput('');
        setTranscript('');
        setSuggestions([]);

        // Add user message immediately
        const optimMsg = {
            role: 'user',
            content: userMsg,
            created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, optimMsg]);
        setLoading(true);

        try {
            const result = await agentApi.chat(userMsg, sessionId);

            if (result.session_id !== sessionId) {
                setSessionId(result.session_id);
                // Refresh conversations list
                loadConversations();
            }

            // Add assistant response
            const aiMsg = {
                role: 'assistant',
                content: result.response,
                tool_results: result.tool_results,
                created_at: new Date().toISOString()
            };
            setMessages(prev => [...prev, aiMsg]);

            // Set quick reply suggestions
            if (result.suggestions && result.suggestions.length > 0) {
                setSuggestions(result.suggestions);
            } else {
                // Default follow-ups
                setSuggestions(["What else can you help with?", "Show me my tasks"]);
            }

            // Update actions if any new ones came back
            if (result.pending_actions && result.pending_actions.length > 0) {
                setPendingActions(prev => {
                    const existingIds = new Set(prev.map(a => a.id));
                    const newActions = result.pending_actions.filter(a => !existingIds.has(a.id));
                    return [...newActions, ...prev];
                });
            }

        } catch (err) {
            console.error('Chat error:', err);
            setMessages(prev => [...prev, {
                role: 'system',
                content: 'Sorry, I encountered an error. Please try again.',
                isError: true,
                created_at: new Date().toISOString()
            }]);
            setSuggestions(["Try again", "Start over"]);
        } finally {
            setLoading(false);
        }
    };

    const handleAction = async (actionId, approved, feedback = null) => {
        // Optimistic update
        setPendingActions(prev => prev.map(a =>
            a.id === actionId
                ? { ...a, status: approved ? 'executing' : 'cancelled' }
                : a
        ));

        try {
            let result;
            if (approved) {
                result = await agentApi.approveAction(actionId);

                if (result.success) {
                    setMessages(prev => [...prev, {
                        role: 'system',
                        content: `✅ Action completed successfully`,
                        created_at: new Date().toISOString()
                    }]);
                }
            } else {
                result = await agentApi.rejectAction(actionId, feedback);
            }

            setPendingActions(prev => prev.filter(a => a.id !== actionId));

        } catch (err) {
            console.error('Action handling error:', err);
            loadPendingActions();
        }
    };

    return (
        <div className={`flex ${isFloating ? 'h-full' : 'h-[calc(100vh-140px)] md:h-[calc(100vh-100px)] max-w-5xl mx-auto'}`}>

            {/* History Sidebar */}
            {showHistory && (
                <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
                    <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                        <span className="font-semibold text-gray-800 dark:text-gray-200">History</span>
                        <button onClick={() => setShowHistory(false)} className="text-gray-500 hover:text-gray-700">
                            ✕
                        </button>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                        {conversations.map((conv, idx) => (
                            <button
                                key={conv.session_id}
                                onClick={() => switchConversation(conv.session_id)}
                                className={`w-full text-left p-3 hover:bg-gray-100 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-700 ${conv.session_id === sessionId ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                                    }`}
                            >
                                <div className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                                    {conv.preview || `Conversation ${idx + 1}`}
                                </div>
                                <div className="text-xs text-gray-500">
                                    {new Date(conv.last_activity_at || conv.started_at).toLocaleDateString()}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-600 to-purple-600">
                    <div className="flex items-center space-x-3">
                        <button
                            onClick={() => setShowHistory(!showHistory)}
                            className="text-white/80 hover:text-white p-1"
                            title="Conversation history"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                            </svg>
                        </button>
                        <span className="text-white font-semibold">LifePilot Assistant</span>
                    </div>
                    <button
                        onClick={startNewChat}
                        className="text-white/80 hover:text-white text-sm px-3 py-1 rounded-full border border-white/30 hover:bg-white/10"
                    >
                        + New Chat
                    </button>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 dark:bg-gray-900/50">
                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-tr-none'
                                    : msg.isError
                                        ? 'bg-red-50 text-red-600 border border-red-200'
                                        : msg.role === 'system'
                                            ? 'bg-gray-100 text-gray-600 text-sm italic mx-auto'
                                            : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-none border border-gray-100 dark:border-gray-700'
                                    }`}
                            >
                                {msg.role === 'user' ? (
                                    <div className="whitespace-pre-wrap">{msg.content}</div>
                                ) : (
                                    <div
                                        className="prose prose-sm dark:prose-invert max-w-none"
                                        dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
                                    />
                                )}

                                {msg.role === 'assistant' && msg.tool_results && msg.tool_results.length > 0 && (
                                    <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 text-xs text-gray-400">
                                        🔧 Used: {msg.tool_results.map(t => t.tool_name).join(', ')}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
                                <div className="flex items-center space-x-2">
                                    <div className="flex space-x-1">
                                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                    <span className="text-sm text-gray-500">Thinking...</span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Quick Reply Suggestions */}
                {suggestions.length > 0 && !loading && (
                    <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-800">
                        <div className="flex flex-wrap gap-2">
                            {suggestions.slice(0, 4).map((suggestion, idx) => (
                                <button
                                    key={idx}
                                    onClick={(e) => handleSend(e, suggestion)}
                                    className="px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full hover:border-blue-400 hover:text-blue-600 transition-colors"
                                >
                                    {suggestion}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Pending Actions Panel */}
                {pendingActions.length > 0 && (
                    <div className="border-t border-gray-200 dark:border-gray-700 bg-yellow-50 dark:bg-yellow-900/10 p-4 max-h-48 overflow-y-auto">
                        <h3 className="text-xs font-semibold text-yellow-800 dark:text-yellow-400 uppercase tracking-wider mb-2">
                            ⚠️ Waiting for approval ({pendingActions.length})
                        </h3>
                        <div className="space-y-2">
                            {pendingActions.map(action => (
                                <div key={action.id} className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-yellow-200 dark:border-yellow-700/50 shadow-sm">
                                    <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                                        <span className="font-medium">{action.action_type}</span>
                                    </div>
                                    {action.status === 'executing' ? (
                                        <div className="text-sm text-blue-600 animate-pulse">Executing...</div>
                                    ) : (
                                        <div className="flex space-x-2">
                                            <button
                                                onClick={() => handleAction(action.id, true)}
                                                className="flex-1 bg-green-600 hover:bg-green-700 text-white text-xs font-medium py-1.5 px-3 rounded-md"
                                            >
                                                ✓ Approve
                                            </button>
                                            <button
                                                onClick={() => handleAction(action.id, false)}
                                                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs font-medium py-1.5 px-3 rounded-md"
                                            >
                                                ✕ Reject
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Input Area */}
                <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
                    <form onSubmit={handleSend} className="relative flex items-center bg-gray-100 dark:bg-gray-900 rounded-xl border border-transparent focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 transition-all">
                        <button
                            type="button"
                            onClick={toggleRecording}
                            className={`p-3 rounded-full transition-colors ${isRecording
                                ? 'text-red-500 animate-pulse'
                                : 'text-gray-500 hover:text-blue-500'
                                }`}
                            title="Voice input"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                            </svg>
                        </button>

                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask LifePilot anything..."
                            className="flex-1 bg-transparent border-none focus:ring-0 py-3 px-2 text-gray-800 dark:text-gray-200 placeholder-gray-400"
                            disabled={loading}
                        />

                        <button
                            type="submit"
                            disabled={!input.trim() || loading}
                            className={`p-2 mr-2 rounded-lg transition-all ${!input.trim() || loading
                                ? 'text-gray-400 cursor-not-allowed'
                                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                                }`}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                            </svg>
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default AgentChat;
