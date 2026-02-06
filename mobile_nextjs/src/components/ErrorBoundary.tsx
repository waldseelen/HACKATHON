/* ── Error Boundary – Catches React render errors ───────── */
'use client';

import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
    children: ReactNode;
    fallback?: ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('[LogSense] React Error Boundary caught:', error, errorInfo);
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback;

            return (
                <div className="flex flex-col items-center justify-center min-h-[300px] px-6 text-center">
                    <AlertTriangle className="w-10 h-10 text-red-400/60 mb-3" />
                    <p className="text-sm font-semibold text-white mb-1">Bir şeyler ters gitti</p>
                    <p className="text-xs text-surface-600 mb-4 max-w-xs">
                        {this.state.error?.message || 'Beklenmeyen bir hata oluştu'}
                    </p>
                    <button
                        onClick={this.handleRetry}
                        className="flex items-center gap-2 text-xs bg-brand-500 text-white px-4 py-2 rounded-lg hover:bg-brand-600 transition-colors"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Tekrar Dene
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
