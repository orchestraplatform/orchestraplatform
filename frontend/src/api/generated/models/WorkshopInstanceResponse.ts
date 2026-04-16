/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for a single workshop instance.
 */
export type WorkshopInstanceResponse = {
    id: string;
    workshopId: string;
    /**
     * Display name of the source template
     */
    workshopName?: (string | null);
    k8sName: string;
    namespace: string;
    ownerEmail: string;
    phase: string;
    url?: (string | null);
    durationRequested: string;
    launchedAt: string;
    expiresAt?: (string | null);
    terminatedAt?: (string | null);
    createdAt: string;
    updatedAt: string;
};

