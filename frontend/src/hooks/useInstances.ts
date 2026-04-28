import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { InstancesService, OpenAPI } from '../api/generated';
import { request as __request } from '../api/generated/core/request';
import type { WorkshopInstanceList } from '../api/generated';

const DETAIL_POLL_MS = 2000;
const INSTANCES_KEY = ['instances'] as const;

export function useInstances(namespace = 'default', page = 1, size = 50) {
  const queryClient = useQueryClient();
  const queryKey = [...INSTANCES_KEY, namespace, page, size];

  // SSE for real-time updates with exponential-backoff reconnect
  useEffect(() => {
    let es: EventSource;
    let retryTimer: ReturnType<typeof setTimeout>;
    let delay = 1_000;
    const MAX_DELAY = 30_000;

    const connect = () => {
      const url = new URL(`${OpenAPI.BASE}/instances/events`, window.location.origin);
      es = new EventSource(url.toString(), { withCredentials: true });

      es.onmessage = (event) => {
        delay = 1_000; // reset backoff on successful message
        try {
          const data: WorkshopInstanceList = JSON.parse(event.data);
          queryClient.setQueryData(queryKey, data);
        } catch (err) {
          console.error('Failed to parse instance events:', err);
        }
      };

      es.onerror = () => {
        es.close();
        retryTimer = setTimeout(() => {
          delay = Math.min(delay * 2, MAX_DELAY);
          connect();
        }, delay);
      };
    };

    connect();

    return () => {
      clearTimeout(retryTimer);
      es?.close();
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

export function useInstanceSummary() {
  return useQuery({
    queryKey: ['instance-summary'],
    queryFn: () =>
      __request<{ totalLaunches: number; launchedLast7Days: number }>(
        OpenAPI, { method: 'GET', url: '/instances/summary' }
      ),
    staleTime: 60_000,
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

export function useExtendInstance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ k8sName, namespace = 'default', extraHours = 1 }: { k8sName: string; namespace?: string; extraHours?: number }) =>
      __request(OpenAPI, {
        method: 'POST',
        url: `/instances/${k8sName}/extend`,
        query: { namespace, extra_hours: extraHours },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INSTANCES_KEY });
    },
  });
}
