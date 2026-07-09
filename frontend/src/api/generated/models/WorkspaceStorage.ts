/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Workspace persistence intent (ADR-0010).
 */
export type WorkspaceStorage = {
    /**
     * Set to 'per-user' to keep each participant's /data on a durable per-(user, workshop) volume that survives session expiry and reattaches on relaunch (ADR-0010). Leave unset for an ephemeral /data that is deleted with the session (the default).
     */
    persist?: (string | null);
};

