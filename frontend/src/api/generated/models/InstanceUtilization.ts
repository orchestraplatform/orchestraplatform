/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Time-in-phase utilization breakdown for a single instance.
 */
export type InstanceUtilization = {
    instanceId: string;
    k8sName: string;
    launchedAt: string;
    terminatedAt?: (string | null);
    /**
     * Wall-clock seconds from launch to now (or termination).
     */
    totalElapsedSeconds: number;
    /**
     * Seconds spent in Ready or Running phase.
     */
    activeSeconds: number;
    /**
     * Seconds spent in each phase, keyed by phase name.
     */
    phaseSeconds: Record<string, number>;
};

