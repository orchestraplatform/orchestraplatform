import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workshopService } from '../services/apiGenerated';
import type { WorkshopCreate } from '../api/generated';

// Poll the workshop list periodically so phase transitions (Creating → Ready)
// appear without a manual refresh.
const WORKSHOP_LIST_POLL_MS = 5_000;
// Individual workshop view polls more frequently to catch per-pod status.
const WORKSHOP_DETAIL_POLL_MS = 2_000;

export function useWorkshops() {
  return useQuery({
    queryKey: ['workshops'],
    queryFn: workshopService.getWorkshops,
    refetchInterval: WORKSHOP_LIST_POLL_MS,
  });
}

export function useWorkshop(name: string) {
  return useQuery({
    queryKey: ['workshop', name],
    queryFn: () => workshopService.getWorkshop(name),
    enabled: !!name,
    refetchInterval: WORKSHOP_DETAIL_POLL_MS,
  });
}

export function useCreateWorkshop() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (workshop: WorkshopCreate) => 
      workshopService.createWorkshop(workshop),
    onSuccess: () => {
      // Invalidate and refetch workshops list
      queryClient.invalidateQueries({ queryKey: ['workshops'] });
    },
  });
}

export function useDeleteWorkshop() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (name: string) => workshopService.deleteWorkshop(name),
    onSuccess: () => {
      // Invalidate and refetch workshops list
      queryClient.invalidateQueries({ queryKey: ['workshops'] });
    },
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: workshopService.getHealth,
    refetchInterval: 30000, // Check health every 30 seconds
  });
}
