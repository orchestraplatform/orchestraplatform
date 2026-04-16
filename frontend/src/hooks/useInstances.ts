import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { InstancesService, OpenAPI } from '../api/generated';
import type { WorkshopInstanceList } from '../api/generated';

const DETAIL_POLL_MS = 2000;
const INSTANCES_KEY = ['instances'] as const;

export function useInstances(namespace = 'default', page = 1, size = 50) {
  const queryClient = useQueryClient();
  const queryKey = [...INSTANCES_KEY, namespace, page, size];

  // SSE for real-time updates
  useEffect(() => {
    const url = new URL(`${OpenAPI.BASE}/instances/events`, window.location.origin);
    const eventSource = new EventSource(url.toString(), { withCredentials: true });

    eventSource.onmessage = (event) => {
      try {
        const data: WorkshopInstanceList = JSON.parse(event.data);
        queryClient.setQueryData(queryKey, data);
      } catch (err) {
        console.error('Failed to parse instance events:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('EventSource failed:', err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [queryClient, queryKey]);

  return useQuery({
    queryKey: queryKey,
    queryFn: () =>
      InstancesService.listInstancesInstancesGet(namespace, page, size),
    // Initial fetch only, SSE handles the rest
    staleTime: Infinity,
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
