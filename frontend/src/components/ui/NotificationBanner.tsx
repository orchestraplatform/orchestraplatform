import React, { useEffect, useState } from 'react';
import { Bell, X } from 'lucide-react';

export function NotificationBanner() {
  const [permission, setPermission] = useState<NotificationPermission>(() =>
    typeof Notification !== 'undefined' ? Notification.permission : 'denied'
  );
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (typeof Notification === 'undefined') return;
    setPermission(Notification.permission);
  }, []);

  if (permission !== 'default' || dismissed) return null;

  const handleAllow = async () => {
    const result = await Notification.requestPermission();
    setPermission(result);
    if (result !== 'default') setDismissed(true);
  };

  return (
    <div className="flex items-center gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-900 mb-4">
      <Bell className="h-4 w-4 shrink-0 text-amber-600" />
      <span className="flex-1">
        Allow notifications to be alerted before your session expires.
      </span>
      <button
        onClick={handleAllow}
        className="rounded-md bg-amber-600 px-3 py-1 text-xs font-medium text-white hover:bg-amber-700 transition-colors"
      >
        Allow
      </button>
      <button
        onClick={() => setDismissed(true)}
        className="text-amber-500 hover:text-amber-700 transition-colors"
        title="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
