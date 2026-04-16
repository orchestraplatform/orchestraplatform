/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopResourceDefaults } from './WorkshopResourceDefaults';
import type { WorkshopStorageDefaults } from './WorkshopStorageDefaults';
/**
 * Request body for updating a workshop template (admin only).
 */
export type WorkshopTemplateUpdate = {
    name?: (string | null);
    description?: (string | null);
    image?: (string | null);
    defaultDuration?: (string | null);
    resources?: (WorkshopResourceDefaults | null);
    storage?: (WorkshopStorageDefaults | null);
    isActive?: (boolean | null);
};

