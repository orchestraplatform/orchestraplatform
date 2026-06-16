/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopResources } from './WorkshopResources';
import type { WorkshopStorage } from './WorkshopStorage';
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
    /**
     * Port the application listens on inside the container (e.g. 8787 for RStudio, 8888 for JupyterLab)
     */
    port?: number;
    /**
     * Extra environment variables for the app container (name -> value). Override operator defaults such as DISABLE_AUTH.
     */
    env?: Record<string, string>;
    /**
     * Container args, replacing the image's default CMD (e.g. JupyterLab launch flags). Leave empty to use the image default.
     */
    args?: Array<string>;
    /**
     * Tenant node-pool tier (small/large). Maps to nodeSelector/tolerations in the operator when tenant pools are enabled.
     */
    tier?: WorkshopTemplateCreate.tier;
    resources?: WorkshopResources;
    storage?: (WorkshopStorage | null);
    /**
     * Category tags for filtering
     */
    tags?: Array<string>;
};
export namespace WorkshopTemplateCreate {
    /**
     * Tenant node-pool tier (small/large). Maps to nodeSelector/tolerations in the operator when tenant pools are enabled.
     */
    export enum tier {
        SMALL = 'small',
        LARGE = 'large',
    }
}

