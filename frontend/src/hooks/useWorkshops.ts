import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workshopService } from '../services/apiGenerated';
import type { WorkshopCreate } from '../api/generated';

export function useWorkshops() {
  return useQuery({
    queryKey: ['workshops'],
    queryFn: workshopService.getWorkshops,
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
  });
}

export function useWorkshop(name: string) {
  return useQuery({
    queryKey: ['workshop', name],
    queryFn: () => workshopService.getWorkshop(name),
    enabled: !!name,
    refetchInterval: 2000, // More frequent updates for individual workshop
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
