/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopCreate } from './WorkshopCreate';
import type { WorkshopStatus } from './WorkshopStatus';
/**
 * Response model for workshop information.
 */
export type WorkshopResponse = {
    name: string;
    namespace: string;
    spec: WorkshopCreate;
    status?: (WorkshopStatus | null);
    created_at?: (string | null);
    updated_at?: (string | null);
};

