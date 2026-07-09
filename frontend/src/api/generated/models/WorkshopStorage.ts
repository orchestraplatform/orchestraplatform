/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkspaceStorage } from './WorkspaceStorage';
/**
 * Workshop storage configuration.
 */
export type WorkshopStorage = {
    /**
     * Storage size
     */
    size?: string;
    /**
     * Storage class name. Leave unset to use the cluster default.
     */
    storageClass?: (string | null);
    /**
     * Workspace persistence intent (ADR-0010). Omit for the ephemeral default.
     */
    workspace?: (WorkspaceStorage | null);
};

