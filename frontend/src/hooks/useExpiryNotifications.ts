import { useCallback, useEffect, useRef } from 'react';
import type { WorkshopInstanceResponse } from '../api/generated';

// Configurable thresholds — adjust here or promote to app config.
export const EXPIRY_WARN_MINUTES = 15;
export const EXPIRY_CRITICAL_MINUTES = 5;

/**
 * Returns the minutes remaining until expiresAt, or Infinity if not set.
 */
export function minutesRemaining(expiresAt: string | null | undefined): number {
  if (!expiresAt) return Infinity;
  return (new Date(expiresAt).getTime() - Date.now()) / 60_000;
}

/**
 * Fires desktop notifications when sessions approach expiry.
 * Tracks already-notified sessions to avoid repeating on every SSE tick.
 */
const CHECK_INTERVAL_MS = 30_000;

export function useExpiryNotifications(instances: WorkshopInstanceResponse[]) {
  const notifiedWarn = useRef<Set<string>>(new Set());
  const notifiedCritical = useRef<Set<string>>(new Set());
  const instancesRef = useRef(instances);

  // Request permission once on first render if not yet decided.
  useEffect(() => {
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const check = useCallback(() => {
    if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return;

    for (const inst of instancesRef.current) {
      const mins = minutesRemaining(inst.expiresAt);
      const name = inst.k8sName;
      const label = inst.workshopName ?? name;

      if (mins <= EXPIRY_CRITICAL_MINUTES && !notifiedCritical.current.has(name)) {
        notifiedCritical.current.add(name);
        const n = new Notification(`Session expiring soon — ${label}`, {
          body: `Your session expires in ${Math.ceil(mins)} minute${Math.ceil(mins) === 1 ? '' : 's'}.`,
          tag: `expiry-critical-${name}`,
        });
        n.onclick = () => { window.focus(); n.close(); };
      } else if (
        mins <= EXPIRY_WARN_MINUTES &&
        mins > EXPIRY_CRITICAL_MINUTES &&
        !notifiedWarn.current.has(name)
      ) {
        notifiedWarn.current.add(name);
        const n = new Notification(`Session expiring — ${label}`, {
          body: `Your session expires in ${Math.ceil(mins)} minutes. Visit My Sessions to extend or save your work.`,
          tag: `expiry-warn-${name}`,
        });
        n.onclick = () => { window.focus(); n.close(); };
      }

      // Clear tracking when a session is no longer near expiry
      // (e.g. user extended it) so we'd notify again if it drops back.
      if (mins > EXPIRY_WARN_MINUTES) {
        notifiedWarn.current.delete(name);
        notifiedCritical.current.delete(name);
      }
    }
  }, []);

  // Update ref and check immediately whenever instances change.
  useEffect(() => {
    instancesRef.current = instances;
    check();
  }, [instances, check]);

  // Also check on a timer in case the user stays on the page without new SSE data.
  useEffect(() => {
    const id = setInterval(check, CHECK_INTERVAL_MS);
    return () => clearInterval(id);
  }, [check]);
}
