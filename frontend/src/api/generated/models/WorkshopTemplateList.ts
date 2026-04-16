/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopTemplateResponse } from './WorkshopTemplateResponse';
/**
 * Paginated list of workshop templates.
 */
export type WorkshopTemplateList = {
    items: Array<WorkshopTemplateResponse>;
    total: number;
    page?: number;
    size?: number;
};

