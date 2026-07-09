/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for launching a workshop instance from a template.
 */
export type WorkshopLaunchRequest = {
    /**
     * Override the template's default duration (e.g. '2h'). If omitted, the template default is used.
     */
    duration?: (string | null);
    /**
     * Kubernetes namespace
     */
    namespace?: (string | null);
    /**
     * Start fresh: terminate the caller's existing active session of this persistence-enabled workshop before launching (ADR-0010 decision F). The durable /data workspace reattaches. Has no effect for ephemeral templates.
     */
    replaceExisting?: boolean;
};

