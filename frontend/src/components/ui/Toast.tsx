import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { X, AlertCircle, CheckCircle, Info } from 'lucide-react';

type ToastType = 'info' | 'success' | 'error';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  addToast: (toast: Omit<Toast, 'id'>) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let nextId = 1;
const DURATION_MS = 5_000;

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), DURATION_MS);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const Icon = toast.type === 'error' ? AlertCircle : toast.type === 'success' ? CheckCircle : Info;
  const colors = {
    error: 'bg-red-50 border-red-200 text-red-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  }[toast.type];
  const iconColors = {
    error: 'text-red-500',
    success: 'text-green-500',
    info: 'text-blue-500',
  }[toast.type];

  return (
    <div className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-md max-w-sm w-full ${colors}`}>
      <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${iconColors}`} />
      <p className="flex-1 text-sm">{toast.message}</p>
      <button onClick={() => onDismiss(toast.id)} className="shrink-0 opacity-60 hover:opacity-100">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    setToasts(prev => [...prev, { ...toast, id: nextId++ }]);
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end">
        {toasts.map(t => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
