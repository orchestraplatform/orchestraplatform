import React from 'react';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="flex h-16 items-center px-4">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-semibold">Orchestra</h1>
            <nav className="flex items-center space-x-6 text-sm font-medium">
              <a
                href="/"
                className="transition-colors hover:text-foreground/80 text-foreground"
              >
                Dashboard
              </a>
              <a
                href="/create"
                className="transition-colors hover:text-foreground/80 text-foreground/60"
              >
                Create Workshop
              </a>
            </nav>
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
