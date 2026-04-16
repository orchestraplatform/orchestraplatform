import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTemplate, useLaunchWorkshop } from '../hooks/useTemplates';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { ArrowLeft, Play, RefreshCw } from 'lucide-react';

export function LaunchWorkshop() {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();

  const { data: template, isLoading, error } = useTemplate(templateId ?? '');
  const launch = useLaunchWorkshop(templateId ?? '');

  const [duration, setDuration] = useState('');
  const [namespace, setNamespace] = useState('default');

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

  const handleLaunch = async () => {
    try {
      const instance = await launch.mutateAsync({
        duration: duration.trim() || null,
        namespace: namespace.trim() || 'default',
      });
      navigate('/', { state: { launched: instance.k8sName } });
    } catch (err) {
      console.error('Failed to launch workshop:', err);
      window.alert('Failed to launch session. Please try again.');
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
          <CardTitle>Launch: {template.name}</CardTitle>
          <CardDescription>{template.description ?? template.image}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="duration">
              Duration
            </label>
            <input
              id="duration"
              type="text"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder={`Default: ${template.defaultDuration}`}
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Leave blank to use the template default ({template.defaultDuration}).
              Examples: 1h, 2h30m, 4h.
            </p>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="namespace">
              Namespace
            </label>
            <input
              id="namespace"
              type="text"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={namespace}
              onChange={(e) => setNamespace(e.target.value)}
            />
          </div>

          <div className="pt-2">
            <Button
              className="w-full"
              onClick={handleLaunch}
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
    </div>
  );
}
