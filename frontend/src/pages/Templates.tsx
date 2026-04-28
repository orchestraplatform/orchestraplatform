import React, { useMemo, useState } from 'react';
import { useTemplates } from '../hooks/useTemplates';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/Card';
import { RefreshCw, Play, Clock, Cpu, HardDrive, Search, X, LayoutGrid, List } from 'lucide-react';
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
        <div className="flex items-start justify-between gap-2">
          <CardTitle>{template.name}</CardTitle>
          <div className="flex items-center gap-1.5 shrink-0">
            {launchCount !== undefined && (
              <span className="text-xs text-muted-foreground whitespace-nowrap">{launchCount.toLocaleString()} launches</span>
            )}
            {!template.isActive && (
              <Badge className="bg-gray-100 text-gray-600 border-gray-200">Archived</Badge>
            )}
          </div>
        </div>
        {template.description && (
          <CardDescription>{template.description}</CardDescription>
        )}
      </CardHeader>

      <CardContent className="flex-grow">
        <div className="flex flex-wrap gap-1.5">
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />{template.defaultDuration}
          </span>
          {template.resources && (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              <Cpu className="h-3 w-3" />
              {template.resources.cpuRequest ?? template.resources.cpu ?? '—'} ·{' '}
              {template.resources.memoryRequest ?? template.resources.memory ?? '—'}
            </span>
          )}
          {template.storage && (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              <HardDrive className="h-3 w-3" />{template.storage.size}
            </span>
          )}
          {template.tags?.map((tag) => (
            <span key={tag} className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary font-medium">
              {tag}
            </span>
          ))}
        </div>
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

interface TemplateRowProps {
  template: WorkshopTemplateResponse;
  launchCount?: number;
}

function TemplateRow({ template, launchCount }: TemplateRowProps) {
  const navigate = useNavigate();

  return (
    <div className="flex items-center gap-4 px-4 py-2.5 border-b last:border-b-0 hover:bg-muted/30 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{template.name}</span>
          {template.tags?.map((tag) => (
            <span key={tag} className="inline-flex items-center rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] text-primary font-medium">
              {tag}
            </span>
          ))}
        </div>
        {template.description && (
          <p className="text-xs text-muted-foreground truncate">{template.description}</p>
        )}
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap hidden sm:block">
        <Clock className="h-3 w-3 inline mr-1" />{template.defaultDuration}
      </span>
      {launchCount !== undefined && (
        <span className="text-xs text-muted-foreground whitespace-nowrap hidden md:block">{launchCount.toLocaleString()} launches</span>
      )}
      <Button
        size="sm"
        disabled={!template.isActive}
        onClick={() => navigate(`/launch/${template.id}`)}
      >
        <Play className="h-3.5 w-3.5 mr-1" />
        Launch
      </Button>
    </div>
  );
}

function matchesDuration(defaultDuration: string, filter: string): boolean {
  const match = defaultDuration.match(/^(\d+(\.\d+)?)(h|m)$/i);
  if (!match) return true;
  const hours = match[3].toLowerCase() === 'h' ? parseFloat(match[1]) : parseFloat(match[1]) / 60;
  switch (filter) {
    case 'under4h':  return hours < 4;
    case '4to8h':    return hours >= 4 && hours <= 8;
    case 'over8h':   return hours > 8;
    default:         return true;
  }
}

type SortOption = 'name-asc' | 'name-desc' | 'newest' | 'oldest';

export function Templates() {
  const { data, isLoading, error, refetch } = useTemplates();
  const { data: statsData } = useTemplateLaunchCounts();
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortOption>('newest');
  const [activeTag, setActiveTag] = useState('');
  const [durationFilter, setDurationFilter] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(
    () => (localStorage.getItem('orchestra:template-view') as 'grid' | 'list') ?? 'grid'
  );

  const setView = (mode: 'grid' | 'list') => {
    setViewMode(mode);
    localStorage.setItem('orchestra:template-view', mode);
  };

  const launchCountMap = useMemo(() => {
    const map: Record<string, number> = {};
    for (const s of statsData ?? []) map[s.templateId] = s.totalLaunches;
    return map;
  }, [statsData]);

  const active = useMemo(() => (data?.items ?? []).filter((t) => t.isActive), [data]);

  const allTags = useMemo(
    () => [...new Set(active.flatMap((t) => t.tags ?? []))].sort(),
    [active]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return [...active]
      .filter((t) => !activeTag || t.tags?.includes(activeTag))
      .filter((t) => !durationFilter || matchesDuration(t.defaultDuration, durationFilter))
      .filter((t) => !q || [t.name, t.description ?? '', t.image, t.slug].some((f) => f.toLowerCase().includes(q)))
      .sort((a, b) => {
        switch (sort) {
          case 'name-asc':  return a.name.localeCompare(b.name);
          case 'name-desc': return b.name.localeCompare(a.name);
          case 'newest':    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
          case 'oldest':    return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        }
      });
  }, [active, activeTag, durationFilter, search, sort]);

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
          <h1 className="text-2xl font-bold tracking-tight">Workshop Templates</h1>
          <p className="text-muted-foreground mt-2">Choose a template to launch a session</p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Search + sort + view toggle */}
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
          value={durationFilter}
          onChange={(e) => setDurationFilter(e.target.value)}
          className="text-sm border rounded-md px-3 py-2 bg-background focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">Any duration</option>
          <option value="under4h">Under 4h</option>
          <option value="4to8h">4–8h</option>
          <option value="over8h">8h+</option>
        </select>
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
        <div className="flex items-center gap-1 border rounded-md p-0.5">
          <button
            onClick={() => setView('grid')}
            className={`rounded p-1.5 transition-colors ${viewMode === 'grid' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            title="Grid view"
          >
            <LayoutGrid className="h-4 w-4" />
          </button>
          <button
            onClick={() => setView('list')}
            className={`rounded p-1.5 transition-colors ${viewMode === 'list' ? 'bg-muted text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            title="List view"
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tag chip filter row */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setActiveTag('')}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors border
              ${!activeTag ? 'bg-foreground text-background border-foreground' : 'bg-background text-muted-foreground border-border hover:border-foreground hover:text-foreground'}`}
          >
            All
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setActiveTag(activeTag === tag ? '' : tag)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors border
                ${activeTag === tag ? 'bg-primary text-primary-foreground border-primary' : 'bg-background text-muted-foreground border-border hover:border-primary hover:text-primary'}`}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="text-center py-12">
          <div className="mx-auto max-w-md">
            {search || activeTag || durationFilter ? (
              <>
                <h3 className="text-lg font-semibold">No templates match the current filters</h3>
                <p className="text-muted-foreground mt-2">Try adjusting your search or filters.</p>
              </>
            ) : (
              <>
                <h3 className="text-lg font-semibold">No templates available</h3>
                <p className="text-muted-foreground mt-2">Ask an administrator to create a workshop template.</p>
              </>
            )}
          </div>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              launchCount={launchCountMap[template.id]}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          {filtered.map((template) => (
            <TemplateRow
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
