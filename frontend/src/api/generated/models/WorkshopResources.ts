/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Workshop resource requirements.
 */
export type WorkshopResources = {
    /**
     * CPU limit
     */
    cpu?: string;
    /**
     * Memory limit
     */
    memory?: string;
    /**
     * CPU request
     */
    cpuRequest?: string;
    /**
     * Memory request
     */
    memoryRequest?: string;
    /**
     * Ephemeral storage limit. Covers everything written outside the /data PVC (package installs, /tmp, container writable layer); the kubelet evicts the pod if exceeded.
     */
    ephemeralStorage?: string;
    /**
     * Ephemeral storage request
     */
    ephemeralStorageRequest?: string;
};

