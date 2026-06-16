import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { TemplatesService } from '../api/generated';
import type { WorkshopLaunchRequest, TemplateStats } from '../api/generated';
import { OpenAPI } from '../api/generated/core/OpenAPI';
import { request as __request } from '../api/generated/core/request';

// Templates are git-managed YAML served read-only by the API (ADR-0006); there
// are no create/update/delete/clone hooks. Edit the files under
// deploy/charts/orchestra/files/templates/ via a pull request.

const TEMPLATES_KEY = ['templates'] as const;

export function useTemplates(page = 1, size = 50, includeInactive = false) {
  return useQuery({
    queryKey: [...TEMPLATES_KEY, page, size, includeInactive],
    queryFn: () =>
      TemplatesService.listTemplatesTemplatesGet(page, size, includeInactive),
  });
}

export function useTemplate(id: string) {
  return useQuery({
    queryKey: [...TEMPLATES_KEY, id],
    queryFn: () => TemplatesService.getTemplateTemplatesTemplateIdGet(id),
    enabled: !!id,
  });
}

export function useLaunchTemplate(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkshopLaunchRequest) =>
      TemplatesService.launchWorkshopTemplatesTemplateIdLaunchPost(templateId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
  });
}

export function useTemplateLaunchCounts() {
  return useQuery({
    queryKey: ['template-stats'],
    queryFn: () =>
      __request<TemplateStats[]>(OpenAPI, { method: 'GET', url: '/templates/stats' }),
    staleTime: 60_000,
  });
}
