/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TemplateStats } from '../models/TemplateStats';
import type { WorkshopInstanceResponse } from '../models/WorkshopInstanceResponse';
import type { WorkshopLaunchRequest } from '../models/WorkshopLaunchRequest';
import type { WorkshopTemplateCreate } from '../models/WorkshopTemplateCreate';
import type { WorkshopTemplateList } from '../models/WorkshopTemplateList';
import type { WorkshopTemplateResponse } from '../models/WorkshopTemplateResponse';
import type { WorkshopTemplateUpdate } from '../models/WorkshopTemplateUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TemplatesService {
    /**
     * List Templates
     * List workshop templates. Inactive templates are hidden unless admin requests them.
     * @param page
     * @param size
     * @param includeInactive
     * @returns WorkshopTemplateList Successful Response
     * @throws ApiError
     */
    public static listTemplatesTemplatesGet(
        page: number = 1,
        size: number = 50,
        includeInactive: boolean = false,
    ): CancelablePromise<WorkshopTemplateList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/templates/',
            query: {
                'page': page,
                'size': size,
                'include_inactive': includeInactive,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Template
     * Create a new workshop template (admin only).
     * @param requestBody
     * @returns WorkshopTemplateResponse Successful Response
     * @throws ApiError
     */
    public static createTemplateTemplatesPost(
        requestBody: WorkshopTemplateCreate,
    ): CancelablePromise<WorkshopTemplateResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/templates/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Template
     * Get a workshop template by ID.
     * @param templateId
     * @returns WorkshopTemplateResponse Successful Response
     * @throws ApiError
     */
    public static getTemplateTemplatesTemplateIdGet(
        templateId: string,
    ): CancelablePromise<WorkshopTemplateResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Template
     * Update a workshop template (admin only).
     * @param templateId
     * @param requestBody
     * @returns WorkshopTemplateResponse Successful Response
     * @throws ApiError
     */
    public static updateTemplateTemplatesTemplateIdPut(
        templateId: string,
        requestBody: WorkshopTemplateUpdate,
    ): CancelablePromise<WorkshopTemplateResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Archive Template
     * Archive a workshop template (admin only). Sets is_active=False; does not hard-delete.
     * @param templateId
     * @returns void
     * @throws ApiError
     */
    public static archiveTemplateTemplatesTemplateIdDelete(
        templateId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Template Stats
     * Aggregate launch and utilization statistics for a template (admin only).
     * @param templateId
     * @returns TemplateStats Successful Response
     * @throws ApiError
     */
    public static getTemplateStatsTemplatesTemplateIdStatsGet(
        templateId: string,
    ): CancelablePromise<TemplateStats> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/templates/{template_id}/stats',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Launch Workshop
     * Launch a new workshop instance from a template.
     *
     * The instance name is auto-generated as ``{slug}-{6-char suffix}``.
     * Duration defaults to the template's default if not supplied.
     * @param templateId
     * @param requestBody
     * @returns WorkshopInstanceResponse Successful Response
     * @throws ApiError
     */
    public static launchWorkshopTemplatesTemplateIdLaunchPost(
        templateId: string,
        requestBody: WorkshopLaunchRequest,
    ): CancelablePromise<WorkshopInstanceResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/templates/{template_id}/launch',
            path: {
                'template_id': templateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
