/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopResponse } from './WorkshopResponse';
/**
 * Response model for workshop list.
 */
export type WorkshopList = {
    items: Array<WorkshopResponse>;
    total: number;
    page?: number;
    size?: number;
};

