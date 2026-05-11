'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import './sidebar.css';

interface QuickLink {
  label: string;
  href: string;
  iconPath: string;
}

interface ModuleLink {
  label: string;
  iconPath: string;
  href?: string;
  status: 'Activo' | 'Próximo';
}

type SidebarProps = {
  collapsed: boolean;
  mobileOpen: boolean;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
};

const QUICK_LINKS: QuickLink[] = [
  {
    label: 'Dashboard',
    href: '/',
    iconPath: '/icons/navigation/dashboard-home.svg'
  },
  {
    label: 'Configuración',
    href: '/settings',
    iconPath: '/icons/navigation/settings-cog-6-tooth.svg'
  }
];

const MODULE_LINKS: ModuleLink[] = [
  {
    label: 'Torre de Control SIO (Minería de Datos)',
    iconPath: '/icons/modules/mining-circle-stack.svg',
    href: '/modules/torre-control-sio',
    status: 'Activo'
  },
  {
    label: 'Margen de Contratos (Series de tiempo)',
    iconPath: '/icons/modules/forecast-presentation-chart-line.svg',
    href: '/modules/forecast',
    status: 'Activo'
  },
  {
    label: 'Rentabilidad B2B (Econometría)',
    iconPath: '/icons/modules/econometrics-banknotes.svg',
    href: '/modules/econometria',
    status: 'Activo'
  },
  {
    label: 'Asistente Inteligente (PLN)',
    iconPath: '/icons/modules/assistant-chat-bubble-left-right.svg',
    href: '/modules/asistente-inteligente',
    status: 'Activo'
  }
];

export default function Sidebar({
  collapsed,
  mobileOpen,
  onToggleCollapsed,
  onCloseMobile
}: SidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }

    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const handleMenuToggle = () => {
    if (mobileOpen) {
      onCloseMobile();
      return;
    }

    onToggleCollapsed();
  };

  return (
    <>
      {mobileOpen ? <button className="sidebar-backdrop" onClick={onCloseMobile} aria-label="Cerrar menú lateral" /> : null}
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo" title="Transfreezer Insight Suite">
            <button
              type="button"
              className="menu-toggle-btn"
              onClick={handleMenuToggle}
              aria-label={mobileOpen ? 'Cerrar menú lateral' : 'Alternar menú lateral'}
              title={mobileOpen ? 'Cerrar menú' : 'Plegar o desplegar menú'}
            >
              <img src="/icons/navigation/menu-bars-3.svg" alt="" aria-hidden="true" />
            </button>
            <span className="logo-icon" aria-hidden="true">TF</span>
            <div className="logo-copy">
              <span className="logo-text">Transfreezer</span>
              <span className="logo-subtext">Insight Suite</span>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <p className="nav-section-title">General</p>
          {QUICK_LINKS.map((item) => (
            <div key={item.label} className="nav-item-group">
              <Link
                href={item.href}
                className={`nav-item ${isActive(item.href) ? 'active' : ''}`}
                title={item.label}
                onClick={onCloseMobile}
              >
                <span className="nav-icon" aria-hidden="true">
                  <img src={item.iconPath} alt="" />
                </span>
                <span className="nav-label">{item.label}</span>
              </Link>
            </div>
          ))}

          <p className="nav-section-title">Módulos</p>
          <div className="nav-submenu modules-list">
            {MODULE_LINKS.map((moduleItem) => (
              <div key={moduleItem.label} className="nav-item-group">
                {moduleItem.href ? (
                  <Link
                    href={moduleItem.href}
                    className={`nav-subitem ${isActive(moduleItem.href) ? 'active' : ''}`}
                    title={moduleItem.label}
                    onClick={onCloseMobile}
                  >
                    <span className="nav-icon" aria-hidden="true">
                      <img src={moduleItem.iconPath} alt="" />
                    </span>
                    <span className="nav-label">{moduleItem.label}</span>
                    <span className={`status-pill ${moduleItem.status === 'Activo' ? 'is-active' : 'is-soon'}`}>
                      {moduleItem.status}
                    </span>
                  </Link>
                ) : (
                  <div className="nav-subitem disabled" title={`${moduleItem.label} - ${moduleItem.status}`}>
                    <span className="nav-icon" aria-hidden="true">
                      <img src={moduleItem.iconPath} alt="" />
                    </span>
                    <span className="nav-label">{moduleItem.label}</span>
                    <span className="status-pill is-soon">{moduleItem.status}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="info-card">
            <p className="info-title">Estado del Sistema</p>
            <p className="info-text">API: <span className="status-badge status-online">Online</span></p>
            <p className="info-text">Modelo: <span className="status-badge status-ready">Listo</span></p>
          </div>
          <div className="user-card" title="Usuario actual">
            <div className="user-avatar">US</div>
            <div className="user-meta">
              <p className="user-name">Usuario empresario</p>
              <p className="user-mail">transfreezer@ops</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
