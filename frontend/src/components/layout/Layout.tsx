import React, { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Badge } from '../ui/Badge';
import { useAuthConfig } from '../../hooks/useAuthConfig';
import { useCurrentUser } from '../../hooks/useCurrentUser';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import {
  LayoutDashboard,
  Rocket,
  History,
  Settings2,
  Monitor,
  LogOut,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Menu,
  X,
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  collapsed: boolean;
  end?: boolean;
  onNavigate?: () => void;
}

function NavItem({ to, icon, label, collapsed, end, onNavigate }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors
         ${isActive
           ? 'bg-white shadow-sm text-foreground font-semibold'
           : 'text-foreground/70 hover:bg-white/60 hover:text-foreground'
         }
         ${collapsed ? 'justify-center px-2' : ''}`
      }
    >
      <span className="shrink-0">{icon}</span>
      {!collapsed && <span>{label}</span>}
    </NavLink>
  );
}

export function Layout({ children }: LayoutProps) {
  const { data: authConfig } = useAuthConfig();
  const { data: user } = useCurrentUser();
  const logoutUrl = authConfig?.logout_url ?? '/oauth2/sign_out';
  const loginUrl = authConfig?.login_url ?? '/oauth2/start';
  const devMode = authConfig?.dev_mode ?? false;

  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // The rail-collapse only applies on desktop; the mobile drawer always shows
  // full labels regardless of the collapsed toggle's remembered state.
  const rail = collapsed && isDesktop;
  const closeMobile = () => setMobileOpen(false);
  // When the drawer is off-screen on mobile, take it out of the tab order and
  // hide it from assistive tech (it's only translated away visually).
  const drawerClosed = !isDesktop && !mobileOpen;

  return (
    <div className="flex min-h-screen bg-background">
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={closeMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar — off-canvas drawer below lg, static rail on lg+ */}
      <aside
        aria-hidden={drawerClosed || undefined}
        inert={drawerClosed ? '' : undefined}
        className={`fixed inset-y-0 left-0 z-40 flex w-56 flex-col border-r bg-slate-50 shrink-0
          transform transition-transform duration-200
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:static lg:translate-x-0 lg:transition-[width]
          ${rail ? 'lg:w-16' : 'lg:w-56'}`}
      >
        {/* Logo + collapse/close toggle */}
        <div className={`flex h-16 items-center border-b ${rail ? 'justify-center px-2' : 'justify-between px-4'}`}>
          {!rail && (
            <Link to="/" onClick={closeMobile} className="flex items-center gap-2 text-sm font-bold tracking-tight">
              <span className="flex h-5 w-5 items-center justify-center rounded bg-foreground text-[10px] font-black text-background">
                O
              </span>
              Orchestra
            </Link>
          )}
          {/* Desktop: collapse rail. Mobile: close drawer. */}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="hidden rounded-md p-1.5 text-foreground/40 hover:bg-muted hover:text-foreground transition-colors lg:inline-flex"
            title={rail ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {rail ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
          <button
            onClick={closeMobile}
            className="rounded-md p-1.5 text-foreground/40 hover:bg-muted hover:text-foreground transition-colors lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Primary nav */}
        <nav className="flex-1 space-y-1 p-2 pt-3">
          <NavItem to="/" icon={<LayoutDashboard className="h-4 w-4" />} label="My Sessions" collapsed={rail} onNavigate={closeMobile} end />
          <NavItem to="/templates" icon={<Rocket className="h-4 w-4" />} label="Launch" collapsed={rail} onNavigate={closeMobile} />
          <NavItem to="/history" icon={<History className="h-4 w-4" />} label="History" collapsed={rail} onNavigate={closeMobile} />
        </nav>

        {/* Admin section */}
        {user?.is_admin && (
          <div className="border-t p-2 pt-3 space-y-1">
            {!rail && (
              <div className="flex items-center gap-1.5 px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <ShieldCheck className="h-3 w-3" />
                Admin
              </div>
            )}
            <NavItem
              to="/admin/sessions"
              icon={<Monitor className="h-4 w-4" />}
              label="Sessions"
              collapsed={rail}
              onNavigate={closeMobile}
            />
            <NavItem
              to="/admin/templates"
              icon={<Settings2 className="h-4 w-4" />}
              label="Templates"
              collapsed={rail}
              onNavigate={closeMobile}
            />
          </div>
        )}

        {/* User identity + sign out */}
        <div className={`border-t p-3 ${rail ? 'flex flex-col items-center gap-2' : ''}`}>
          {devMode && !rail && (
            <div className="mb-2">
              <Badge variant="secondary">Dev mode</Badge>
            </div>
          )}
          {user ? (
            <>
              {rail ? (
                <a
                  href={logoutUrl}
                  title="Sign out"
                  className="flex justify-center p-1.5 rounded-md text-foreground/60 hover:bg-muted hover:text-foreground transition-colors"
                >
                  <LogOut className="h-4 w-4 shrink-0" />
                </a>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    {user.email[0].toUpperCase()}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium text-foreground">{user.email}</div>
                    <a href={logoutUrl} className="text-xs text-muted-foreground hover:text-foreground transition-colors">Sign out</a>
                  </div>
                  {user.is_admin && (
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 shrink-0">admin</Badge>
                  )}
                </div>
              )}
            </>
          ) : !devMode ? (
            <a
              href={loginUrl}
              className="text-sm font-medium text-primary hover:underline"
            >
              {rail ? '→' : 'Sign in'}
            </a>
          ) : null}
        </div>
      </aside>

      {/* Main content — min-w-0 lets flex children (tables) shrink and scroll
          instead of forcing the page wider than the viewport. */}
      <div className="flex min-w-0 flex-1 flex-col overflow-auto">
        {/* Mobile top bar with the drawer toggle (hidden on lg+) */}
        <div className="flex h-14 items-center gap-3 border-b bg-slate-50 px-4 lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1.5 text-foreground/60 hover:bg-muted hover:text-foreground transition-colors"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <Link to="/" className="flex items-center gap-2 text-sm font-bold tracking-tight">
            <span className="flex h-5 w-5 items-center justify-center rounded bg-foreground text-[10px] font-black text-background">
              O
            </span>
            Orchestra
          </Link>
        </div>
        <main className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
          {children}
        </main>
      </div>
    </div>
  );
}
