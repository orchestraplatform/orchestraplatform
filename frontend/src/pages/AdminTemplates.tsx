import React from 'react';
import { useTemplates } from '../hooks/useTemplates';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { RefreshCw, GitBranch } from 'lucide-react';

// Templates are git-managed YAML (ADR-0006). This view is read-only: the catalog
// is changed by editing files under deploy/charts/orchestra/files/templates/ via
// a pull request, not through the UI.
export function AdminTemplates() {
  const { data, isLoading, refetch } = useTemplates(1, 100, true);

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

  const templates = data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workshop Templates</h1>
          <p className="text-muted-foreground mt-1">
            Read-only view of the workshop environment blueprints.
          </p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="flex items-start space-x-2 rounded-md border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
        <GitBranch className="h-4 w-4 mt-0.5 shrink-0" />
        <p>
          Templates are managed in git under{' '}
          <code className="font-mono text-xs">deploy/charts/orchestra/files/templates/</code>.
          To add, change, or retire one, open a pull request — changes roll out on the next deploy.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>All Templates</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Slug</th>
                  <th className="px-4 py-3">Image</th>
                  <th className="px-4 py-3">Tier</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {templates.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      No templates found.
                    </td>
                  </tr>
                ) : (
                  templates.map((t) => (
                    <tr key={t.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium">{t.name}</td>
                      <td className="px-4 py-3 font-mono text-xs">{t.slug}</td>
                      <td className="px-4 py-3 font-mono text-xs max-w-[200px] truncate">
                        {t.image}
                      </td>
                      <td className="px-4 py-3">
                        <Badge className="bg-slate-100 text-slate-700 border-slate-200">
                          {t.tier ?? 'small'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        {t.isActive ? (
                          <Badge className="bg-green-100 text-green-700 border-green-200">Enabled</Badge>
                        ) : (
                          <Badge className="bg-gray-100 text-gray-600 border-gray-200">Disabled</Badge>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
