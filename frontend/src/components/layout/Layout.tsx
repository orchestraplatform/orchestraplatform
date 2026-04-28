import React, { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Badge } from '../ui/Badge';
import { useAuthConfig } from '../../hooks/useAuthConfig';
import { useCurrentUser } from '../../hooks/useCurrentUser';
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
}

function NavItem({ to, icon, label, collapsed, end }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end={end}
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

  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r bg-slate-50 transition-all duration-200 shrink-0
          ${collapsed ? 'w-16' : 'w-56'}`}
      >
        {/* Logo + collapse toggle */}
        <div className={`flex h-16 items-center border-b ${collapsed ? 'justify-center px-2' : 'justify-between px-4'}`}>
          {!collapsed && (
            <Link to="/" className="flex items-center gap-2 text-sm font-bold tracking-tight">
              <span className="flex h-5 w-5 items-center justify-center rounded bg-foreground text-[10px] font-black text-background">
                O
              </span>
              Orchestra
            </Link>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="rounded-md p-1.5 text-foreground/40 hover:bg-muted hover:text-foreground transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* Primary nav */}
        <nav className="flex-1 space-y-1 p-2 pt-3">
          <NavItem to="/" icon={<LayoutDashboard className="h-4 w-4" />} label="My Sessions" collapsed={collapsed} end />
          <NavItem to="/templates" icon={<Rocket className="h-4 w-4" />} label="Launch" collapsed={collapsed} />
          <NavItem to="/history" icon={<History className="h-4 w-4" />} label="History" collapsed={collapsed} />
        </nav>

        {/* Admin section */}
        {user?.is_admin && (
          <div className="border-t p-2 pt-3 space-y-1">
            {!collapsed && (
              <div className="flex items-center gap-1.5 px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <ShieldCheck className="h-3 w-3" />
                Admin
              </div>
            )}
            <NavItem
              to="/admin/sessions"
              icon={<Monitor className="h-4 w-4" />}
              label="Sessions"
              collapsed={collapsed}
            />
            <NavItem
              to="/admin/templates"
              icon={<Settings2 className="h-4 w-4" />}
              label="Templates"
              collapsed={collapsed}
            />
          </div>
        )}

        {/* User identity + sign out */}
        <div className={`border-t p-3 ${collapsed ? 'flex flex-col items-center gap-2' : ''}`}>
          {devMode && !collapsed && (
            <div className="mb-2">
              <Badge variant="secondary">Dev mode</Badge>
            </div>
          )}
          {user ? (
            <>
              {collapsed ? (
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
              {collapsed ? '→' : 'Sign in'}
            </a>
          ) : null}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <main className="mx-auto max-w-5xl px-6 py-6">
          {children}
        </main>
      </div>
    </div>
  );
}
