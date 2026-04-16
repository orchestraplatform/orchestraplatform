import React from 'react';
import { History as HistoryIcon } from 'lucide-react';

export function History() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3 text-muted-foreground">
      <HistoryIcon className="h-10 w-10 opacity-30" />
      <p className="text-sm">Session history coming soon.</p>
    </div>
  );
}
