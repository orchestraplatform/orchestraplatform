import React, { useEffect, useState } from 'react';
import { useCreateTemplate, useUpdateTemplate } from '../../hooks/useTemplates';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { WorkshopTemplateResponse, WorkshopTemplateCreate, WorkshopTemplateUpdate } from '../../api/generated';
import { parseArgs, parseEnv, serializeArgs, serializeEnv } from '../../utils/envArgs';

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
  // env/args are edited as text (dotenv lines / one arg per line) and parsed on submit.
  const [envText, setEnvText] = useState('');
  const [argsText, setArgsText] = useState('');
  const [envError, setEnvError] = useState<string | null>(null);
  const [argsError, setArgsError] = useState<string | null>(null);

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
      setEnvText(serializeEnv(template.env));
      setArgsText(serializeArgs(template.args));
    } else {
      setFormData(DEFAULT_CREATE_VALUES);
      setEnvText('');
      setArgsText('');
    }
    setEnvError(null);
    setArgsError(null);
  }, [template, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const env = parseEnv(envText);
    const args = parseArgs(argsText);
    if (env.error || args.error) {
      setEnvError(env.error);
      setArgsError(args.error);
      return;
    }
    const payload: WorkshopTemplateCreate = { ...formData, env: env.value, args: args.value };
    try {
      if (template) {
        await updateTemplate.mutateAsync({
          id: template.id,
          body: payload as WorkshopTemplateUpdate,
        });
      } else {
        await createTemplate.mutateAsync(payload);
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

        <div className="space-y-2">
          <p className="text-sm font-medium">Advanced</p>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground" htmlFor="env">
              Environment variables
            </label>
            <textarea
              id="env"
              spellCheck={false}
              placeholder={'DISABLE_AUTH=false\nMY_FLAG=1'}
              className="flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={envText}
              onChange={e => {
                setEnvText(e.target.value);
                setEnvError(parseEnv(e.target.value).error);
              }}
            />
            <p className="text-xs text-muted-foreground">
              One <code>KEY=value</code> per line. Overrides operator defaults (e.g. <code>DISABLE_AUTH</code>).
            </p>
            {envError && <p className="text-xs text-destructive">{envError}</p>}
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground" htmlFor="args">
              Container args
            </label>
            <textarea
              id="args"
              spellCheck={false}
              placeholder={"start-notebook.py\n--ServerApp.token="}
              className="flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={argsText}
              onChange={e => {
                setArgsText(e.target.value);
                setArgsError(parseArgs(e.target.value).error);
              }}
            />
            <p className="text-xs text-muted-foreground">
              One argument per line. Replaces the image's default command. Leave empty to use the image default.
            </p>
            {argsError && <p className="text-xs text-destructive">{argsError}</p>}
          </div>
        </div>

        <div className="border-t pt-4 mt-6 flex justify-end space-x-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending || !!envError || !!argsError}>
            {isPending ? 'Saving...' : template ? 'Update Template' : 'Create Template'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
