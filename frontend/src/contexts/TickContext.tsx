import React, { createContext, useContext, useEffect, useState } from 'react';

const TickContext = createContext(0);

export function TickProvider({ intervalMs, children }: { intervalMs: number; children: React.ReactNode }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(n => n + 1), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return <TickContext.Provider value={tick}>{children}</TickContext.Provider>;
}

export function useTick() {
  useContext(TickContext); // subscribe — re-renders consumer on each tick
}
