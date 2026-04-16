/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopInstanceResponse } from './WorkshopInstanceResponse';
/**
 * Paginated list of workshop instances.
 */
export type WorkshopInstanceList = {
    items: Array<WorkshopInstanceResponse>;
    total: number;
    page?: number;
    size?: number;
};

