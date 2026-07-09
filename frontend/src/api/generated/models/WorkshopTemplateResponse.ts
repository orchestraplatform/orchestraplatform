/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopResources } from './WorkshopResources';
import type { WorkshopStorage } from './WorkshopStorage';
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
    port?: number;
    env?: Record<string, string>;
    args?: Array<string>;
    tier?: WorkshopTemplateResponse.tier;
    resources: WorkshopResources;
    storage?: (WorkshopStorage | null);
    tags?: Array<'bioconductor' | 'jupyter' | 'python' | 'rstudio'>;
    url?: (string | null);
    sourceUrl?: (string | null);
    submittedBy?: (string | null);
    isActive: boolean;
    createdBy: string;
    createdAt: string;
    updatedAt: string;
};
export namespace WorkshopTemplateResponse {
    export enum tier {
        SMALL = 'small',
        LARGE = 'large',
    }
}

