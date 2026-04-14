/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
    /**
     * Readiness Check
     * Readiness check for Kubernetes.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static readinessCheckReadyGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/ready',
        });
    }
    /**
     * Liveness Check
     * Liveness check for Kubernetes.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static livenessCheckLiveGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/live',
        });
    }
}
