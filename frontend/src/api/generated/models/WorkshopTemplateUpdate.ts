/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopResources } from './WorkshopResources';
import type { WorkshopStorage } from './WorkshopStorage';
/**
 * Request body for updating a workshop template (admin only).
 */
export type WorkshopTemplateUpdate = {
    name?: (string | null);
    description?: (string | null);
    image?: (string | null);
    defaultDuration?: (string | null);
    port?: (number | null);
    env?: (Record<string, string> | null);
    args?: (Array<string> | null);
    tier?: ('small' | 'large' | null);
    resources?: (WorkshopResources | null);
    storage?: (WorkshopStorage | null);
    tags?: (Array<string> | null);
    isActive?: (boolean | null);
};

