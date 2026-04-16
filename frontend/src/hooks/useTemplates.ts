import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { TemplatesService, InstancesService } from '../api/generated';
import type { WorkshopLaunchRequest } from '../api/generated';

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

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkshopTemplateCreate) =>
      TemplatesService.createTemplateTemplatesPost(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WorkshopTemplateUpdate }) =>
      TemplatesService.updateTemplateTemplatesTemplateIdPut(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}

export function useToggleTemplateActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      TemplatesService.toggleTemplateActiveTemplatesTemplateIdToggleActivePatch(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, hard = false }: { id: string; hard?: boolean }) =>
      TemplatesService.deleteTemplateTemplatesTemplateIdDelete(id, hard),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}
