import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { InstancesService } from '../api/generated';

const POLL_MS = 5000;
const DETAIL_POLL_MS = 2000;
const INSTANCES_KEY = ['instances'] as const;

export function useInstances(namespace = 'default', page = 1, size = 50) {
  return useQuery({
    queryKey: [...INSTANCES_KEY, namespace, page, size],
    queryFn: () =>
      InstancesService.listInstancesInstancesGet(namespace, page, size),
    refetchInterval: POLL_MS,
  });
}

export function useInstance(k8sName: string, namespace = 'default') {
  return useQuery({
    queryKey: [...INSTANCES_KEY, k8sName, namespace],
    queryFn: () =>
      InstancesService.getInstanceInstancesK8SNameGet(k8sName, namespace),
    enabled: !!k8sName,
    refetchInterval: DETAIL_POLL_MS,
  });
}

export function useTerminateInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ k8sName, namespace = 'default' }: { k8sName: string; namespace?: string }) =>
      InstancesService.terminateInstanceInstancesK8SNameDelete(k8sName, namespace),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INSTANCES_KEY });
    },
  });
}
