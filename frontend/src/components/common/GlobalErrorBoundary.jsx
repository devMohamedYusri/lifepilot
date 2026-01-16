import React from 'react';

/**
 * Global Error Boundary
 * Catches unhandled errors in the component tree and displays a friendly fallback UI.
 */
class GlobalErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error) {
        // Update state so the next render will show the fallback UI.
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        // You can also log the error to an error reporting service
        console.error("Uncaught error:", error, errorInfo);
        this.setState({ errorInfo });
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-surface-950 flex flex-col items-center justify-center p-4">
                    <div className="glass max-w-md w-full p-8 rounded-2xl border border-red-500/20 text-center space-y-6">
                        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto">
                            <span className="text-3xl">🧩</span>
                        </div>

                        <div>
                            <h1 className="text-2xl font-bold text-white mb-2">Something went wrong</h1>
                            <p className="text-surface-300">
                                LifePilot encountered an unexpected error.
                                We've logged this issue and our team will look into it.
                            </p>
                        </div>

                        {/* Error details (dev only) */}
                        {import.meta.env.DEV && this.state.error && (
                            <div className="text-left bg-surface-900/50 p-4 rounded-lg border border-surface-800 overflow-auto max-h-40 text-xs font-mono text-red-300">
                                {this.state.error.toString()}
                            </div>
                        )}

                        <div className="flex flex-col gap-3">
                            <button
                                onClick={this.handleRetry}
                                className="btn-primary w-full py-3"
                            >
                                🔄 Refresh Application
                            </button>
                            <button
                                onClick={() => this.setState({ hasError: false })}
                                className="btn-ghost text-surface-400 hover:text-white"
                            >
                                Try to continue (may be unstable)
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default GlobalErrorBoundary;
