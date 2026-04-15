import axios from 'axios';
import { OpenAPI, WorkshopsService, HealthService } from '../api/generated';
import type {
  WorkshopResponse,
  WorkshopCreate,
  WorkshopList
} from '../api/generated';

// Configure the generated API client
OpenAPI.BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Redirect to oauth2-proxy login on 401.
// The `rd` parameter tells oauth2-proxy where to send the user after login.
axios.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401) {
      const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/oauth2/start?rd=${returnTo}`;
    }
    return Promise.reject(error);
  }
);

export interface CurrentUser {
  email: string;
  is_admin: boolean;
}

/** Fetch the authenticated user's identity from the API. */
export async function getCurrentUser(): Promise<CurrentUser> {
  const base = OpenAPI.BASE;
  const response = await axios.get<CurrentUser>(`${base}/auth/me`, {
    withCredentials: true,
  });
  return response.data;
}

// Re-export the generated services for easy use
export { WorkshopsService, HealthService };

// Re-export types
export type { 
  WorkshopResponse as Workshop,
  WorkshopCreate as CreateWorkshopRequest,
  WorkshopList as WorkshopListResponse 
} from '../api/generated';

// Convenience wrapper that matches our existing service interface
export const workshopService = {
  // Get all workshops (matches our existing interface)
  getWorkshops: async (): Promise<WorkshopList> => {
    return WorkshopsService.listWorkshopsWorkshopsGet();
  },

  // Get specific workshop
  getWorkshop: async (name: string, namespace = 'default'): Promise<WorkshopResponse> => {
    return WorkshopsService.getWorkshopWorkshopsWorkshopNameGet(name, namespace);
  },

  // Create new workshop
  createWorkshop: async (workshop: WorkshopCreate, namespace = 'default'): Promise<WorkshopResponse> => {
    return WorkshopsService.createWorkshopWorkshopsPost(workshop, namespace);
  },

  // Delete workshop
  deleteWorkshop: async (name: string, namespace = 'default'): Promise<void> => {
    return WorkshopsService.deleteWorkshopWorkshopsWorkshopNameDelete(name, namespace);
  },

  // Get workshop status
  getWorkshopStatus: async (name: string, namespace = 'default') => {
    return WorkshopsService.getWorkshopStatusWorkshopsWorkshopNameStatusGet(name, namespace);
  },

  // Health checks
  getHealth: async () => {
    return HealthService.livenessCheckLiveGet();
  },

  getReady: async () => {
    return HealthService.readinessCheckReadyGet();
  },
};
