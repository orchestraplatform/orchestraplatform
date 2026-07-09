/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopInstanceResponse } from './WorkshopInstanceResponse';
/**
 * 409 body when the caller already has an active session of a
 * persistence-enabled workshop (ADR-0010 decision F).
 *
 * The client offers Continue (use ``instance``) or Start fresh (relaunch
 * with ``replaceExisting=true``).
 */
export type LaunchConflict = {
    /**
     * Machine-readable discriminator for the conflict body.
     */
    error: string;
    instance: WorkshopInstanceResponse;
};

