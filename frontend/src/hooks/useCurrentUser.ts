import { useQuery } from '@tanstack/react-query';
import { getCurrentUser } from '../services/apiGenerated';

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: getCurrentUser,
    // Identity rarely changes; refetch only on window focus
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
