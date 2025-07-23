/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkshopCreate } from '../models/WorkshopCreate';
import type { WorkshopList } from '../models/WorkshopList';
import type { WorkshopResponse } from '../models/WorkshopResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WorkshopsService {
    /**
     * Create Workshop
     * Create a new workshop.
     * @param requestBody
     * @param namespace Kubernetes namespace
     * @returns WorkshopResponse Successful Response
     * @throws ApiError
     */
    public static createWorkshopWorkshopsPost(
        requestBody: WorkshopCreate,
        namespace: string = 'default',
    ): CancelablePromise<WorkshopResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/workshops/',
            query: {
                'namespace': namespace,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Workshops
     * List workshops in a namespace.
     * @param namespace Kubernetes namespace
     * @param page Page number
     * @param size Page size
     * @returns WorkshopList Successful Response
     * @throws ApiError
     */
    public static listWorkshopsWorkshopsGet(
        namespace: string = 'default',
        page: number = 1,
        size: number = 50,
    ): CancelablePromise<WorkshopList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/workshops/',
            query: {
                'namespace': namespace,
                'page': page,
                'size': size,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Workshop
     * Get a workshop by name.
     * @param workshopName Workshop name
     * @param namespace Kubernetes namespace
     * @returns WorkshopResponse Successful Response
     * @throws ApiError
     */
    public static getWorkshopWorkshopsWorkshopNameGet(
        workshopName: string,
        namespace: string = 'default',
    ): CancelablePromise<WorkshopResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/workshops/{workshop_name}',
            path: {
                'workshop_name': workshopName,
            },
            query: {
                'namespace': namespace,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Workshop
     * Delete a workshop.
     * @param workshopName Workshop name
     * @param namespace Kubernetes namespace
     * @returns void
     * @throws ApiError
     */
    public static deleteWorkshopWorkshopsWorkshopNameDelete(
        workshopName: string,
        namespace: string = 'default',
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/workshops/{workshop_name}',
            path: {
                'workshop_name': workshopName,
            },
            query: {
                'namespace': namespace,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Workshop Status
     * Get workshop status information.
     * @param workshopName Workshop name
     * @param namespace Kubernetes namespace
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getWorkshopStatusWorkshopsWorkshopNameStatusGet(
        workshopName: string,
        namespace: string = 'default',
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/workshops/{workshop_name}/status',
            path: {
                'workshop_name': workshopName,
            },
            query: {
                'namespace': namespace,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
