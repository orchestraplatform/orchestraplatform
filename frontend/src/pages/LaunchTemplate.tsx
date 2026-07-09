import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import { useTemplate, useLaunchTemplate } from '../hooks/useTemplates';
import { ApiError } from '../api/generated';
import type { LaunchConflict } from '../api/generated';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { useToast } from '../components/ui/Toast';
import { track } from '../utils/analytics';
import { ArrowLeft, ExternalLink, Play, RefreshCw } from 'lucide-react';

export function LaunchTemplate() {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();

  const { data: template, isLoading, error } = useTemplate(templateId ?? '');
  const launch = useLaunchTemplate(templateId ?? '');
  const { addToast } = useToast();

  const [duration, setDuration] = useState('');
  // Existing active session of this persistence-enabled workshop (409 body,
  // ADR-0010 decision F): the user chooses Continue or Start fresh.
  const [conflict, setConflict] = useState<LaunchConflict | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading template...</span>
        </div>
      </div>
    );
  }

  if (error || !template) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-destructive">Template not found</h2>
          <p className="text-muted-foreground mt-2">
            The requested template does not exist or is no longer available.
          </p>
        </div>
        <Link to="/templates">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Templates
          </Button>
        </Link>
      </div>
    );
  }

  // Guard the copy: a template can load with partial/empty fields, and we never
  // want "undefined" or an empty "()" leaking into the heading or help text.
  const name = template.name?.trim();
  const defaultDuration = template.defaultDuration?.trim();
  const description = template.description?.trim();
  // Only surface http(s) links — a javascript:/data: href in author-supplied
  // metadata would run despite rel="noopener". (The API also validates these,
  // but the UI shouldn't trust it.)
  const httpUrl = (raw?: string | null): string | undefined => {
    const v = raw?.trim();
    if (!v) return undefined;
    try {
      const { protocol } = new URL(v);
      return protocol === 'http:' || protocol === 'https:' ? v : undefined;
    } catch {
      return undefined;
    }
  };
  const url = httpUrl(template.url);
  const sourceUrl = httpUrl(template.sourceUrl);

  const handleLaunch = async (replaceExisting = false) => {
    setConflict(null);
    track('workshop_launch', { template_slug: template.slug, replace_existing: replaceExisting });
    try {
      const instance = await launch.mutateAsync({
        duration: duration.trim() || null,
        replaceExisting,
      });
      track('workshop_launch_result', { template_slug: template.slug, outcome: 'success' });
      navigate('/', { state: { launched: instance.k8sName } });
    } catch (err) {
      if (
        err instanceof ApiError &&
        err.status === 409 &&
        err.body?.error === 'active_session_exists'
      ) {
        track('workshop_launch_result', { template_slug: template.slug, outcome: 'conflict' });
        setConflict(err.body as LaunchConflict);
        return;
      }
      track('workshop_launch_result', { template_slug: template.slug, outcome: 'error' });
      console.error('Failed to launch workshop:', err);
      addToast({ type: 'error', message: 'Failed to launch session. Please try again.' });
    }
  };

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <div className="flex items-center space-x-2">
        <Link to="/templates">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Templates
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{name ? `Launch: ${name}` : 'Launch Session'}</CardTitle>
          <CardDescription>{template.image}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {description && (
            <div className="text-sm text-muted-foreground space-y-2 [&_a]:text-primary [&_a]:underline [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_code]:font-mono">
              <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{description}</ReactMarkdown>
            </div>
          )}

          {(url || sourceUrl) && (
            <div className="flex flex-wrap gap-4 text-sm">
              {url && (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-primary underline"
                >
                  <ExternalLink className="h-3.5 w-3.5 mr-1" />
                  Learn more
                </a>
              )}
              {sourceUrl && (
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-primary underline"
                >
                  <ExternalLink className="h-3.5 w-3.5 mr-1" />
                  Source
                </a>
              )}
            </div>
          )}

          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="duration">
              Duration
            </label>
            <input
              id="duration"
              type="text"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder={defaultDuration ? `Default: ${defaultDuration}` : 'e.g. 2h'}
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Leave blank to use the template default
              {defaultDuration ? ` (${defaultDuration})` : ''}.
              Examples: 1h, 2h30m, 4h.
            </p>
          </div>

          <div className="pt-2">
            <Button
              className="w-full"
              onClick={() => handleLaunch()}
              disabled={launch.isPending || !template.isActive}
            >
              {launch.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Launching...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Launch Session
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        isOpen={conflict !== null}
        title="You already have a session for this workshop"
        message="Continue in your existing session, or start fresh. Starting fresh ends the current session; files saved in /data carry over."
        cancelLabel="Continue"
        confirmLabel="Start fresh (ends the current one)"
        onCancel={() => {
          track('launch_conflict_choice', { template_slug: template.slug, choice: 'continue' });
          navigate('/', { state: { launched: conflict?.instance.k8sName } });
        }}
        onConfirm={() => {
          track('launch_conflict_choice', { template_slug: template.slug, choice: 'start_fresh' });
          handleLaunch(true);
        }}
      />
    </div>
  );
}
