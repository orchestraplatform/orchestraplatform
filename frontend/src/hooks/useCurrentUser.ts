import { useQuery } from '@tanstack/react-query';
import { AuthenticationService } from '../api/generated';

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: () => AuthenticationService.getCurrentUserInfoAuthMeGet(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
