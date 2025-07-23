export interface Workshop {
  name: string;
  namespace?: string;
  spec: WorkshopSpec;
  status?: WorkshopStatus;
  created_at?: string;
  updated_at?: string;
  // Computed fields for display
  description?: string;
  image?: string;
  resources?: WorkshopResources;
  duration?: string;
  expires_at?: string;
  connection_info?: ConnectionInfo;
}

export interface WorkshopSpec {
  name: string;
  duration: string;
  participants?: number;
  image: string;
  resources: {
    cpu: string;
    memory: string;
    cpuRequest?: string;
    memoryRequest?: string;
  };
  storage: {
    size: string;
    storageClass?: string | null;
  };
  ingress?: {
    host?: string;
    annotations?: Record<string, string>;
  } | null;
}

export interface WorkshopResources {
  cpu: string;
  memory: string;
  storage: string;
}

export interface WorkshopStatus {
  phase: WorkshopPhase;
  ready: boolean;
  message?: string;
  last_updated?: string;
}

export interface ConnectionInfo {
  url?: string;
  username?: string;
  password?: string;
}

export type WorkshopPhase = 
  | 'Pending'
  | 'Creating'
  | 'Running'
  | 'Failed'
  | 'Expiring'
  | 'Expired';

export interface CreateWorkshopRequest {
  name: string;
  description?: string;
  image: string;
  resources: WorkshopResources;
  duration: string;
}

export interface WorkshopListResponse {
  items: Workshop[];
  total: number;
  page: number;
  size: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version?: string;
}
