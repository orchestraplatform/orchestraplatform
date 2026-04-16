/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
    /**
     * Health Check
     * Basic health check endpoint.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthCheckHealthGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health/',
        });
    }
    /**
     * Readiness Check
     * Readiness check for Kubernetes.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readinessCheckHealthReadyGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health/ready',
        });
    }
    /**
     * Liveness Check
     * Liveness check for Kubernetes.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static livenessCheckHealthLiveGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health/live',
        });
    }
}
