import React from 'react';
import { useCurrentUser } from '../../hooks/useCurrentUser';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { data: user } = useCurrentUser();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="flex h-16 items-center justify-between px-4">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold">Orchestra</h1>
            <nav className="flex items-center space-x-6 text-sm font-medium">
              <a
                href="/"
                className="transition-colors hover:text-foreground/80 text-foreground"
              >
                My Sessions
              </a>
              <a
                href="/templates"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                Templates
              </a>
            </nav>
          </div>

          {/* User identity + logout */}
          <div className="flex items-center space-x-3 text-sm">
            {user && (
              <>
                <span className="text-foreground/70">{user.email}</span>
                {user.is_admin && (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    admin
                  </span>
                )}
                <a
                  href="/oauth2/sign_out"
                  className="transition-colors hover:text-foreground/80 text-foreground/60"
                >
                  Sign out
                </a>
              </>
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
