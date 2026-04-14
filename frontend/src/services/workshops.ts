import apiClient from './api';
import type { 
  Workshop, 
  CreateWorkshopRequest, 
  WorkshopListResponse,
  HealthResponse 
} from '../types';

export const workshopService = {
  // Get all workshops
  getWorkshops: async (): Promise<WorkshopListResponse> => {
    const response = await apiClient.get('/workshops/');
    return response.data;
  },

  // Get specific workshop
  getWorkshop: async (name: string): Promise<Workshop> => {
    const response = await apiClient.get(`/workshops/${name}/`);
    return response.data;
  },

  // Create new workshop
  createWorkshop: async (workshop: CreateWorkshopRequest): Promise<Workshop> => {
    const response = await apiClient.post('/workshops/', workshop);
    return response.data;
  },

  // Delete workshop
  deleteWorkshop: async (name: string): Promise<void> => {
    await apiClient.delete(`/workshops/${name}/`);
  },

  // Get health status
  getHealth: async (): Promise<HealthResponse> => {
    const response = await apiClient.get('/');
    return response.data;
  },

  // Get readiness status  
  getReady: async (): Promise<HealthResponse> => {
    const response = await apiClient.get('/ready/');
    return response.data;
  },
};
