import React, { useEffect, useState } from 'react';
import { useCreateTemplate, useUpdateTemplate } from '../../hooks/useTemplates';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { WorkshopTemplateResponse, WorkshopTemplateCreate, WorkshopTemplateUpdate } from '../../api/generated';

interface TemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  template?: WorkshopTemplateResponse | null;
}

const DEFAULT_CREATE_VALUES: WorkshopTemplateCreate = {
  name: '',
  slug: '',
  description: '',
  image: 'rocker/rstudio:latest',
  defaultDuration: '4h',
  port: 8787,
  resources: {
    cpu: '1',
    memory: '2Gi',
    cpuRequest: '500m',
    memoryRequest: '1Gi',
  },
  storage: {
    size: '10Gi',
  }
};

export function TemplateModal({ isOpen, onClose, template }: TemplateModalProps) {
  const createTemplate = useCreateTemplate();
  const updateTemplate = useUpdateTemplate();
  const [formData, setFormData] = useState<WorkshopTemplateCreate>(DEFAULT_CREATE_VALUES);

  useEffect(() => {
    if (template) {
      setFormData({
        name: template.name,
        slug: template.slug,
        description: template.description || '',
        image: template.image,
        defaultDuration: template.defaultDuration,
        port: template.port ?? DEFAULT_CREATE_VALUES.port,
        resources: template.resources || DEFAULT_CREATE_VALUES.resources,
        storage: template.storage || DEFAULT_CREATE_VALUES.storage,
      });
    } else {
      setFormData(DEFAULT_CREATE_VALUES);
    }
  }, [template, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (template) {
        await updateTemplate.mutateAsync({
          id: template.id,
          body: formData as WorkshopTemplateUpdate,
        });
      } else {
        await createTemplate.mutateAsync(formData);
      }
      onClose();
    } catch (err) {
      console.error('Failed to save template:', err);
    }
  };

  const isPending = createTemplate.isPending || updateTemplate.isPending;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={template ? 'Edit Template' : 'Create Template'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="name">Name</label>
            <input
              id="name"
              required
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="slug">Slug</label>
            <input
              id="slug"
              required
              disabled={!!template}
              placeholder="e.g. rstudio"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
              value={formData.slug}
              onChange={e => setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="description">Description</label>
          <textarea
            id="description"
            className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            value={formData.description || ''}
            onChange={e => setFormData({ ...formData, description: e.target.value })}
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium" htmlFor="image">Docker Image</label>
          <input
            id="image"
            required
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            value={formData.image}
            onChange={e => setFormData({ ...formData, image: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="duration">Default Duration</label>
            <input
              id="duration"
              placeholder="4h"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={formData.defaultDuration}
              onChange={e => setFormData({ ...formData, defaultDuration: e.target.value })}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="port">App Port</label>
            <input
              id="port"
              type="number"
              min={1}
              max={65535}
              placeholder="8787"
              title="Port the application listens on inside the container (e.g. 8787 for RStudio, 8888 for JupyterLab)"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={formData.port ?? ''}
              onChange={e => setFormData({ ...formData, port: e.target.value === '' ? undefined : Number(e.target.value) })}
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="storage">Storage Size</label>
            <input
              id="storage"
              placeholder="10Gi"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={formData.storage?.size || ''}
              onChange={e => setFormData({ ...formData, storage: { size: e.target.value } })}
            />
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium">Resources</p>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="cpu">CPU Limit</label>
              <input
                id="cpu"
                placeholder="1"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.resources?.cpu || ''}
                onChange={e => setFormData({ ...formData, resources: { ...formData.resources, cpu: e.target.value } })}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="memory">Memory Limit</label>
              <input
                id="memory"
                placeholder="2Gi"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.resources?.memory || ''}
                onChange={e => setFormData({ ...formData, resources: { ...formData.resources, memory: e.target.value } })}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="cpuRequest">CPU Request</label>
              <input
                id="cpuRequest"
                placeholder="500m"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.resources?.cpuRequest || ''}
                onChange={e => setFormData({ ...formData, resources: { ...formData.resources, cpuRequest: e.target.value } })}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="memoryRequest">Memory Request</label>
              <input
                id="memoryRequest"
                placeholder="1Gi"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={formData.resources?.memoryRequest || ''}
                onChange={e => setFormData({ ...formData, resources: { ...formData.resources, memoryRequest: e.target.value } })}
              />
            </div>
          </div>
        </div>

        <div className="border-t pt-4 mt-6 flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending}>
            {isPending ? 'Saving...' : template ? 'Update Template' : 'Create Template'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
