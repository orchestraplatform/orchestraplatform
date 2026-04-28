/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopResourceDefaults } from './WorkshopResourceDefaults';
import type { WorkshopStorageDefaults } from './WorkshopStorageDefaults';
/**
 * Response schema for a workshop template.
 */
export type WorkshopTemplateResponse = {
    id: string;
    name: string;
    slug: string;
    description?: (string | null);
    image: string;
    defaultDuration: string;
    resources: WorkshopResourceDefaults;
    storage?: (WorkshopStorageDefaults | null);
    tags: Array<string>;
    isActive: boolean;
    createdBy: string;
    createdAt: string;
    updatedAt: string;
};

