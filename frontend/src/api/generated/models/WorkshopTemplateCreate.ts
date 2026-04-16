/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopResourceDefaults } from './WorkshopResourceDefaults';
import type { WorkshopStorageDefaults } from './WorkshopStorageDefaults';
/**
 * Request body for creating a workshop template (admin only).
 */
export type WorkshopTemplateCreate = {
    /**
     * Human-readable display name
     */
    name: string;
    /**
     * k8s-safe identifier used as prefix for instance names (max 40 chars)
     */
    slug: string;
    /**
     * Optional description
     */
    description?: (string | null);
    /**
     * Default Docker image
     */
    image?: string;
    /**
     * Default session duration
     */
    defaultDuration?: string;
    resources?: WorkshopResourceDefaults;
    storage?: (WorkshopStorageDefaults | null);
};

