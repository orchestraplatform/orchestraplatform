import React from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { useAuthConfig } from '../../hooks/useAuthConfig';
import { useCurrentUser } from '../../hooks/useCurrentUser';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { data: authConfig } = useAuthConfig();
  const { data: user } = useCurrentUser();
  const logoutUrl = authConfig?.logout_url ?? '/oauth2/sign_out';
  const loginUrl = authConfig?.login_url ?? '/oauth2/start';
  const devMode = authConfig?.dev_mode ?? false;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="flex h-16 items-center justify-between px-4">
          <div className="flex items-center space-x-4">
            <Link to="/" className="text-xl font-semibold">
              Orchestra
            </Link>
            <nav className="flex items-center space-x-6 text-sm font-medium">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `transition-colors hover:text-foreground/80 ${
                    isActive ? 'text-foreground' : 'text-foreground/60'
                  }`
                }
              >
                My Sessions
              </NavLink>
              <NavLink
                to="/templates"
                className={({ isActive }) =>
                  `transition-colors hover:text-foreground/80 ${
                    isActive ? 'text-foreground' : 'text-foreground/60'
                  }`
                }
              >
                Templates
              </NavLink>
            </nav>
          </div>

          {/* User identity + logout */}
          <div className="flex items-center space-x-3 text-sm">
            {devMode && <Badge variant="secondary">Dev mode</Badge>}
            {user && (
              <>
                <span className="text-foreground/70">{user.email}</span>
                {user.is_admin && (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    admin
                  </span>
                )}
                <a
                  href={logoutUrl}
                  className="transition-colors hover:text-foreground/80 text-foreground/60"
                >
                  Sign out
                </a>
              </>
            )}
            {!user && !devMode && (
              <a href={loginUrl}>
                <Button size="sm">Sign in</Button>
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  );
}
