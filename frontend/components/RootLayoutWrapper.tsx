'use client';

import { useEffect, useRef, useState } from 'react';
import AssistantFAB from './AssistantFAB';
import Sidebar from './Sidebar';
import './root-layout.css';

const SIDEBAR_TRANSITION_MS = 240;

export default function RootLayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [layoutCollapsed, setLayoutCollapsed] = useState(false);
  const [sidebarResizing, setSidebarResizing] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const resizeTimeoutRef = useRef<number | null>(null);

  const dispatchLayoutResize = () => {
    // Recharts and other responsive components react to this event after layout settles.
    window.dispatchEvent(new Event('resize'));
    window.requestAnimationFrame(() => {
      window.dispatchEvent(new Event('resize'));
    });
  };

  const handleToggleCollapsed = () => {
    setSidebarCollapsed((previous) => {
      const next = !previous;

      setSidebarResizing(true);

      if (resizeTimeoutRef.current !== null) {
        window.clearTimeout(resizeTimeoutRef.current);
      }

      resizeTimeoutRef.current = window.setTimeout(() => {
        setLayoutCollapsed(next);
        window.requestAnimationFrame(() => {
          dispatchLayoutResize();
          window.setTimeout(() => {
            setSidebarResizing(false);
          }, 40);
        });
      }, SIDEBAR_TRANSITION_MS);

      return next;
    });
  };

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth > 768) {
        setMobileOpen(false);
      }
    };

    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    return () => {
      if (resizeTimeoutRef.current !== null) {
        window.clearTimeout(resizeTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className={`root-layout ${layoutCollapsed ? 'sidebar-collapsed' : ''} ${sidebarResizing ? 'sidebar-resizing' : ''}`}>
      <Sidebar
        collapsed={sidebarCollapsed}
        mobileOpen={mobileOpen}
        onToggleCollapsed={handleToggleCollapsed}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <main className="main-content">
        <button
          type="button"
          className="mobile-menu-btn"
          aria-label="Abrir menú lateral"
          onClick={() => setMobileOpen(true)}
        >
          <img src="/icons/navigation/menu-bars-3.svg" alt="" aria-hidden="true" />
          <span className="mobile-menu-label">Menú</span>
        </button>
        {children}
      </main>
      <AssistantFAB />
    </div>
  );
}
