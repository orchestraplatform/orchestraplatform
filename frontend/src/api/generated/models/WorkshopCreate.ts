/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopIngress } from './WorkshopIngress';
import type { WorkshopResources } from './WorkshopResources';
import type { WorkshopStorage } from './WorkshopStorage';
/**
 * Request model for creating a workshop.
 */
export type WorkshopCreate = {
    /**
     * Workshop name
     */
    name: string;
    /**
     * Workshop duration
     */
    duration?: string;
    /**
     * RStudio image
     */
    image?: string;
    resources?: WorkshopResources;
    storage?: (WorkshopStorage | null);
    ingress?: (WorkshopIngress | null);
};

