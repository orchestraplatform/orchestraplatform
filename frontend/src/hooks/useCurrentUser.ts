import { useQuery } from '@tanstack/react-query';
import { AuthenticationService } from '../api/generated';

export interface CurrentUser {
  email: string;
  is_admin: boolean;
}

function toCurrentUser(data: Record<string, unknown>): CurrentUser {
  return {
    email: String(data.email ?? ''),
    is_admin: Boolean(data.is_admin),
  };
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async () =>
      toCurrentUser(await AuthenticationService.getCurrentUserInfoAuthMeGet()),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
