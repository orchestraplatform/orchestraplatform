/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Aggregate utilization statistics for a workshop template.
 */
export type TemplateStats = {
    templateId: string;
    totalLaunches: number;
    activeInstances: number;
    /**
     * Sum of active_seconds across all instances of this template.
     */
    totalActiveSeconds: number;
    uniqueUsers: number;
};

