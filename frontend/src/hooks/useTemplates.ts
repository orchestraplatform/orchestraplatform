import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { TemplatesService, InstancesService } from '../api/generated';
import type { WorkshopLaunchRequest } from '../api/generated';

const TEMPLATES_KEY = ['templates'] as const;

export function useTemplates(page = 1, size = 50) {
  return useQuery({
    queryKey: [...TEMPLATES_KEY, page, size],
    queryFn: () =>
      TemplatesService.listTemplatesTemplatesGet(page, size, false),
  });
}

export function useTemplate(id: string) {
  return useQuery({
    queryKey: [...TEMPLATES_KEY, id],
    queryFn: () => TemplatesService.getTemplateTemplatesTemplateIdGet(id),
    enabled: !!id,
  });
}

export function useLaunchWorkshop(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkshopLaunchRequest) =>
      TemplatesService.launchWorkshopTemplatesTemplateIdLaunchPost(templateId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
    },
  });
}
