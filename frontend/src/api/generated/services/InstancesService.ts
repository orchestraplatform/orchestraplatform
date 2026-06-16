/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InstanceSummary } from '../models/InstanceSummary';
import type { InstanceUtilization } from '../models/InstanceUtilization';
import type { WorkshopInstanceList } from '../models/WorkshopInstanceList';
import type { WorkshopInstanceResponse } from '../models/WorkshopInstanceResponse';
import type { WorkshopInstanceStatus } from '../models/WorkshopInstanceStatus';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class InstancesService {
    /**
     * List Instances
     * List running workshop instances.
     *
     * Regular users see only their own. Admins see all.
     * @param namespace
     * @param page
     * @param size
     * @returns WorkshopInstanceList Successful Response
     * @throws ApiError
     */
    public static listInstancesInstancesGet(
        namespace: string = 'default',
        page: number = 1,
        size: number = 50,
    ): CancelablePromise<WorkshopInstanceList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/instances/',
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
     * Get Instance Summary
     * Aggregate launch counts all-time and over the last 7 days (admin only).
     * @returns InstanceSummary Successful Response
     * @throws ApiError
     */
    public static getInstanceSummaryInstancesSummaryGet(): CancelablePromise<InstanceSummary> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/instances/summary',
        });
    }
    /**
     * Instance Events
     * Stream workshop instance updates for the current user.
     *
     * Passes the session factory rather than a held session so the generator
     * acquires and releases a connection on each poll cycle instead of holding
     * one open for the entire stream lifetime.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static instanceEventsInstancesEventsGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/instances/events',
        });
    }
    /**
     * Get Instance
     * Get a workshop instance, syncing live status from k8s.
     * @param k8SName Workshop instance k8s name
     * @param namespace
     * @returns WorkshopInstanceResponse Successful Response
     * @throws ApiError
     */
    public static getInstanceInstancesK8SNameGet(
        k8SName: string,
        namespace: string = 'default',
    ): CancelablePromise<WorkshopInstanceResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/instances/{k8s_name}',
            path: {
                'k8s_name': k8SName,
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
     * Terminate Instance
     * Terminate a workshop instance (deletes k8s CRD + marks DB record terminated).
     * @param k8SName Workshop instance k8s name
     * @param namespace
     * @returns void
     * @throws ApiError
     */
    public static terminateInstanceInstancesK8SNameDelete(
        k8SName: string,
        namespace: string = 'default',
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/instances/{k8s_name}',
            path: {
                'k8s_name': k8SName,
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
     * Extend Instance
     * Extend an active workshop instance's expiry by extra_hours (default +1h).
     * @param k8SName Workshop instance k8s name
     * @param namespace
     * @param extraHours
     * @returns WorkshopInstanceResponse Successful Response
     * @throws ApiError
     */
    public static extendInstanceInstancesK8SNameExtendPost(
        k8SName: string,
        namespace: string = 'default',
        extraHours: number = 1,
    ): CancelablePromise<WorkshopInstanceResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/instances/{k8s_name}/extend',
            path: {
                'k8s_name': k8SName,
            },
            query: {
                'namespace': namespace,
                'extra_hours': extraHours,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Instance Utilization
     * Time-in-phase utilization breakdown for a workshop instance.
     * @param k8SName Workshop instance k8s name
     * @param namespace
     * @returns InstanceUtilization Successful Response
     * @throws ApiError
     */
    public static getInstanceUtilizationInstancesK8SNameUtilizationGet(
        k8SName: string,
        namespace: string = 'default',
    ): CancelablePromise<InstanceUtilization> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/instances/{k8s_name}/utilization',
            path: {
                'k8s_name': k8SName,
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
     * Get Instance Status
     * Lightweight status and URL for a workshop instance.
     * @param k8SName Workshop instance k8s name
     * @param namespace
     * @returns WorkshopInstanceStatus Successful Response
     * @throws ApiError
     */
    public static getInstanceStatusInstancesK8SNameStatusGet(
        k8SName: string,
        namespace: string = 'default',
    ): CancelablePromise<WorkshopInstanceStatus> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/instances/{k8s_name}/status',
            path: {
                'k8s_name': k8SName,
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
