import React from 'react';
import { History as HistoryIcon } from 'lucide-react';

export function History() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3 text-muted-foreground">
      <HistoryIcon className="h-10 w-10 opacity-20" />
      <p className="text-sm font-medium text-foreground/70">History coming soon</p>
      <p className="text-xs text-muted-foreground text-center max-w-xs">
        Once launched, past sessions will appear here with duration, template, and status.
      </p>
    </div>
  );
}
