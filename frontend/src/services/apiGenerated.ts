import { OpenAPI, WorkshopsService, HealthService } from '../api/generated';
import type { 
  WorkshopResponse, 
  WorkshopCreate, 
  WorkshopList 
} from '../api/generated';

// Configure the generated API client
OpenAPI.BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
