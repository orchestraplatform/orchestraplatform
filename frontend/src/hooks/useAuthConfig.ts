import { useQuery } from '@tanstack/react-query';
import { AuthenticationService } from '../api/generated';

export interface AuthConfig {
  login_url: string;
  logout_url: string;
  dev_mode: boolean;
}

function toAuthConfig(data: Record<string, unknown>): AuthConfig {
  return {
    login_url: String(data.login_url ?? '/oauth2/start'),
    logout_url: String(data.logout_url ?? '/oauth2/sign_out'),
    dev_mode: Boolean(data.dev_mode),
  };
}

export function useAuthConfig() {
  return useQuery({
    queryKey: ['authConfig'],
    queryFn: async () =>
      toAuthConfig(await AuthenticationService.getAuthConfigAuthAuthConfigGet()),
    staleTime: Infinity, // auth config doesn't change at runtime
  });
}
