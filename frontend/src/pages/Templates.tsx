import React, { useMemo, useState } from 'react';
import { useTemplates } from '../hooks/useTemplates';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/Card';
import { RefreshCw, Play, Clock, Cpu, HardDrive, Search, X, Rocket } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { WorkshopTemplateResponse } from '../api/generated';
import { useTemplateLaunchCounts } from '../hooks/useTemplates';

interface TemplateCardProps {
  template: WorkshopTemplateResponse;
  launchCount?: number;
}

function TemplateCard({ template, launchCount }: TemplateCardProps) {
  const navigate = useNavigate();

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{template.name}</CardTitle>
          {!template.isActive && (
            <Badge className="bg-gray-100 text-gray-600 border-gray-200">Archived</Badge>
          )}
        </div>
        <CardDescription>{template.description ?? template.image}</CardDescription>
      </CardHeader>

      <CardContent className="flex-grow space-y-2">
        <div className="flex items-center text-sm text-muted-foreground space-x-1">
          <Clock className="h-3.5 w-3.5 shrink-0" />
          <span>Default duration: {template.defaultDuration}</span>
        </div>
        {template.resources && (
          <div className="flex items-center text-sm text-muted-foreground space-x-1">
            <Cpu className="h-3.5 w-3.5 shrink-0" />
            <span>
              CPU: {template.resources.cpuRequest ?? template.resources.cpu ?? '—'} /
              Mem: {template.resources.memoryRequest ?? template.resources.memory ?? '—'}
            </span>
          </div>
        )}
        {template.storage && (
          <div className="flex items-center text-sm text-muted-foreground space-x-1">
            <HardDrive className="h-3.5 w-3.5 shrink-0" />
            <span>Storage: {template.storage.size}</span>
          </div>
        )}
        <div className="text-xs text-muted-foreground font-mono pt-1">{template.image}</div>
        {launchCount !== undefined && (
          <div className="flex items-center text-sm text-muted-foreground space-x-1 pt-1">
            <Rocket className="h-3.5 w-3.5 shrink-0" />
            <span>{launchCount.toLocaleString()} {launchCount === 1 ? 'launch' : 'launches'}</span>
          </div>
        )}
      </CardContent>

      <CardFooter>
        <Button
          className="w-full"
          disabled={!template.isActive}
          onClick={() => navigate(`/launch/${template.id}`)}
        >
          <Play className="h-4 w-4 mr-2" />
          Launch
        </Button>
      </CardFooter>
    </Card>
  );
}

type SortOption = 'name-asc' | 'name-desc' | 'newest' | 'oldest';

export function Templates() {
  const { data, isLoading, error, refetch } = useTemplates();
  const { data: statsData } = useTemplateLaunchCounts();
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortOption>('newest');

  const launchCountMap = useMemo(() => {
    const map: Record<string, number> = {};
    for (const s of statsData ?? []) map[s.templateId] = s.totalLaunches;
    return map;
  }, [statsData]);

  const active = useMemo(() => (data?.items ?? []).filter((t) => t.isActive), [data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const matches = q
      ? active.filter((t) =>
          [t.name, t.description ?? '', t.image, t.slug]
            .some((field) => field.toLowerCase().includes(q))
        )
      : active;

    return [...matches].sort((a, b) => {
      switch (sort) {
        case 'name-asc':  return a.name.localeCompare(b.name);
        case 'name-desc': return b.name.localeCompare(a.name);
        case 'newest':    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'oldest':    return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      }
    });
  }, [active, search, sort]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading templates...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-destructive">Failed to load templates</h2>
          <p className="text-muted-foreground mt-2">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
        </div>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Workshop Templates</h1>
          <p className="text-muted-foreground mt-2">Choose a template to launch a session</p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            placeholder="Search templates…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOption)}
          className="text-sm border rounded-md px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="name-asc">Name (A–Z)</option>
          <option value="name-desc">Name (Z–A)</option>
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
        </select>
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {filtered.length} of {active.length}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12">
          <div className="mx-auto max-w-md">
            {search ? (
              <>
                <h3 className="text-lg font-semibold">No templates match "{search}"</h3>
                <p className="text-muted-foreground mt-2">Try a different search term.</p>
              </>
            ) : (
              <>
                <h3 className="text-lg font-semibold">No templates available</h3>
                <p className="text-muted-foreground mt-2">Ask an administrator to create a workshop template.</p>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              launchCount={launchCountMap[template.id]}
            />
          ))}
        </div>
      )}
    </div>
  );
}
