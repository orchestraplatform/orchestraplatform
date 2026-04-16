import React, { useState } from 'react';
import { useTemplates, useToggleTemplateActive, useDeleteTemplate } from '../hooks/useTemplates';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { RefreshCw, Plus, Trash2, Archive, ArchiveRestore, BarChart3, Edit } from 'lucide-react';
import { TemplateModal } from '../components/workshop/TemplateModal';
import type { WorkshopTemplateResponse } from '../api/generated';

export function AdminTemplates() {
  const { data, isLoading, refetch } = useTemplates(1, 100, true);
  const toggleActive = useToggleTemplateActive();
  const deleteTemplate = useDeleteTemplate();
  
  const [modalOpen, setModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<WorkshopTemplateResponse | null>(null);

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

  const handleToggle = async (id: string) => {
    try {
      await toggleActive.mutateAsync(id);
    } catch (err) {
      console.error('Failed to toggle template status:', err);
    }
  };

  const handleEdit = (template: WorkshopTemplateResponse) => {
    setEditingTemplate(template);
    setModalOpen(true);
  };

  const handleCreate = () => {
    setEditingTemplate(null);
    setModalOpen(true);
  };

  const handleDelete = async (id: string, hard = false) => {
    const msg = hard 
      ? 'Are you sure you want to PERMANENTLY delete this template? This cannot be undone.'
      : 'Are you sure you want to archive this template? It will be hidden from users.';
    
    if (window.confirm(msg)) {
      try {
        await deleteTemplate.mutateAsync({ id, hard });
      } catch (err) {
        console.error('Failed to delete template:', err);
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Manage Templates</h1>
          <p className="text-muted-foreground mt-2">
            Admin console for workshop environment blueprints
          </p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => refetch()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button size="sm" onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Create Template
          </Button>
        </div>
      </div>

      <TemplateModal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        template={editingTemplate} 
      />

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
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
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
                        {t.isActive ? (
                          <Badge className="bg-green-100 text-green-700 border-green-200">Active</Badge>
                        ) : (
                          <Badge className="bg-gray-100 text-gray-600 border-gray-200">Archived</Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right space-x-1">
                        <Button variant="ghost" size="icon" title="Stats">
                          <BarChart3 className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" title="Edit" onClick={() => handleEdit(t)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          title={t.isActive ? "Archive" : "Unarchive"}
                          onClick={() => handleToggle(t.id)}
                        >
                          {t.isActive ? <Archive className="h-4 w-4 text-amber-600" /> : <ArchiveRestore className="h-4 w-4 text-blue-600" />}
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          title="Delete Permanently"
                          onClick={() => handleDelete(t.id, true)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
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
