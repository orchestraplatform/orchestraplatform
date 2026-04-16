import React, { useMemo, useState } from 'react';
import { useInstances, useTerminateInstance } from '../hooks/useInstances';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { RefreshCw, Search, X, Trash2, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import { formatAbsoluteTime, getTimeRemaining } from '../utils';
import type { WorkshopInstanceResponse } from '../api/generated';

type SortField = 'ownerEmail' | 'workshopName' | 'k8sName' | 'phase' | 'launchedAt' | 'expiresAt';
type SortDir = 'asc' | 'desc';

const PHASE_COLORS: Record<string, string> = {
  Ready:       'bg-green-100 text-green-800 border-green-200',
  Running:     'bg-green-100 text-green-800 border-green-200',
  Pending:     'bg-yellow-100 text-yellow-800 border-yellow-200',
  Creating:    'bg-yellow-100 text-yellow-800 border-yellow-200',
  Failed:      'bg-red-100 text-red-800 border-red-200',
  Terminating: 'bg-gray-100 text-gray-800 border-gray-200',
};

function SortIcon({ field, sortField, sortDir }: { field: SortField; sortField: SortField; sortDir: SortDir }) {
  if (field !== sortField) return <ChevronsUpDown className="h-3.5 w-3.5 opacity-40" />;
  return sortDir === 'asc'
    ? <ChevronUp className="h-3.5 w-3.5" />
    : <ChevronDown className="h-3.5 w-3.5" />;
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-lg border bg-card px-4 py-3">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
    </div>
  );
}

export function AdminDashboard() {
  const { data, isLoading, error, refetch } = useInstances('default', 1, 100);
  const terminate = useTerminateInstance();

  const [search, setSearch] = useState('');
  const [phaseFilter, setPhaseFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('launchedAt');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const instances = data?.items ?? [];

  const stats = useMemo(() => ({
    total:       instances.length,
    ready:       instances.filter(i => i.phase === 'Ready' || i.phase === 'Running').length,
    transitional: instances.filter(i => i.phase === 'Pending' || i.phase === 'Creating').length,
    failed:      instances.filter(i => i.phase === 'Failed').length,
  }), [instances]);

  const phases = useMemo(() =>
    [...new Set(instances.map(i => i.phase))].sort(),
    [instances]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return instances
      .filter(i => !phaseFilter || i.phase === phaseFilter)
      .filter(i => !q || [i.ownerEmail, i.workshopName ?? '', i.k8sName, i.namespace]
        .some(f => f.toLowerCase().includes(q)))
      .sort((a, b) => {
        const mul = sortDir === 'asc' ? 1 : -1;
        const av = a[sortField] ?? '';
        const bv = b[sortField] ?? '';
        return String(av).localeCompare(String(bv)) * mul;
      });
  }, [instances, search, phaseFilter, sortField, sortDir]);

  const handleSort = (field: SortField) => {
    if (field === sortField) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  };

  const handleTerminate = async (inst: WorkshopInstanceResponse) => {
    if (!window.confirm(`Terminate session "${inst.k8sName}" for ${inst.ownerEmail}?`)) return;
    try {
      await terminate.mutateAsync({ k8sName: inst.k8sName, namespace: inst.namespace });
    } catch {
      window.alert('Failed to terminate session.');
    }
  };

  const Th = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th
      className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide cursor-pointer select-none hover:text-foreground whitespace-nowrap"
      onClick={() => handleSort(field)}
    >
      <span className="flex items-center gap-1">
        {children}
        <SortIcon field={field} sortField={sortField} sortDir={sortDir} />
      </span>
    </th>
  );

  if (isLoading) return (
    <div className="flex items-center justify-center min-h-[400px]">
      <RefreshCw className="h-4 w-4 animate-spin mr-2" />
      <span>Loading sessions…</span>
    </div>
  );

  if (error) return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <p className="text-destructive font-semibold">Failed to load sessions</p>
      <Button variant="outline" onClick={() => refetch()}>
        <RefreshCw className="h-4 w-4 mr-2" /> Try Again
      </Button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Session Dashboard</h1>
          <p className="text-muted-foreground mt-1">All active workshop sessions</p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Total active" value={stats.total} color="text-foreground" />
        <StatCard label="Ready / Running" value={stats.ready} color="text-green-600" />
        <StatCard label="Starting up" value={stats.transitional} color="text-yellow-600" />
        <StatCard label="Failed" value={stats.failed} color="text-red-600" />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search user, template, instance…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <select
          value={phaseFilter}
          onChange={e => setPhaseFilter(e.target.value)}
          className="text-sm border rounded-md px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All phases</option>
          {phases.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {filtered.length} of {instances.length}
        </span>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground text-sm">
          {instances.length === 0 ? 'No active sessions.' : 'No sessions match the current filters.'}
        </div>
      ) : (
        <div className="rounded-md border overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40">
              <tr>
                <Th field="ownerEmail">User</Th>
                <Th field="workshopName">Template</Th>
                <Th field="k8sName">Instance</Th>
                <Th field="phase">Phase</Th>
                <Th field="launchedAt">Started</Th>
                <Th field="expiresAt">Expires</Th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map(inst => (
                <tr key={inst.k8sName} className="hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2.5 text-xs text-muted-foreground max-w-[180px] truncate" title={inst.ownerEmail}>
                    {inst.ownerEmail}
                  </td>
                  <td className="px-3 py-2.5 font-medium">{inst.workshopName ?? '—'}</td>
                  <td className="px-3 py-2.5 font-mono text-xs">{inst.k8sName}</td>
                  <td className="px-3 py-2.5">
                    <Badge className={PHASE_COLORS[inst.phase] ?? 'bg-blue-100 text-blue-800'}>
                      {inst.phase}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 text-muted-foreground whitespace-nowrap">
                    {formatAbsoluteTime(inst.launchedAt)}
                  </td>
                  <td className="px-3 py-2.5 text-muted-foreground whitespace-nowrap">
                    {inst.expiresAt ? (
                      <span>{formatAbsoluteTime(inst.expiresAt)}
                        <span className="ml-1 text-xs">({getTimeRemaining(inst.expiresAt)})</span>
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-3 py-2.5">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleTerminate(inst)}
                      disabled={terminate.isPending}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
