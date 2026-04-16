import React from 'react';
import { useTemplates } from '../hooks/useTemplates';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/Card';
import { RefreshCw, Play, Clock, Cpu, HardDrive } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import type { WorkshopTemplateResponse } from '../api/generated';

interface TemplateCardProps {
  template: WorkshopTemplateResponse;
}

function TemplateCard({ template }: TemplateCardProps) {
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

export function Templates() {
  const { data, isLoading, error, refetch } = useTemplates();

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

  const templates = data?.items ?? [];
  const active = templates.filter((t) => t.isActive);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Workshop Templates</h1>
          <p className="text-muted-foreground mt-2">
            Choose a template to launch a session
          </p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {active.length === 0 ? (
        <div className="text-center py-12">
          <div className="mx-auto max-w-md">
            <h3 className="text-lg font-semibold">No templates available</h3>
            <p className="text-muted-foreground mt-2">
              Ask an administrator to create a workshop template.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {active.map((template) => (
            <TemplateCard key={template.id} template={template} />
          ))}
        </div>
      )}
    </div>
  );
}
