'use client';
import React from 'react';

interface Props {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

interface State { hasError: boolean; message: string }

export default class SpatialErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, message: '' };

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err?.message || 'Unknown spatial error' };
  }

  componentDidCatch(err: Error) {
    // eslint-disable-next-line no-console
    console.error('[spatial] error:', err);
  }

  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}
