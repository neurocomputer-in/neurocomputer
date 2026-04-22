'use client';

/**
 * Thin wrapper — the real NeuroIDE lives as a pane component
 * (components/neuroide/NeuroIDEPanel.tsx) so it can mount inside
 * split panes alongside chat + terminal. Visiting /graph directly
 * renders it full-screen for deep-linking.
 */

import NeuroIDEPanel from '@/components/neuroide/NeuroIDEPanel';

export default function GraphPage() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <NeuroIDEPanel />
    </div>
  );
}
