/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Lightweight status/URL response for a workshop instance.
 */
export type WorkshopInstanceStatus = {
    id: string;
    k8sName: string;
    phase: string;
    url?: (string | null);
    expiresAt?: (string | null);
};

