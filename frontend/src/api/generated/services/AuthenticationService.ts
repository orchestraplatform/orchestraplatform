/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthenticationService {
    /**
     * Get Current User Info
     * Return the identity of the currently authenticated user.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getCurrentUserInfoAuthMeGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/me',
        });
    }
    /**
     * Get Auth Config
     * Return auth endpoint URLs for the frontend.
     *
     * The frontend uses these to redirect unauthenticated users to the oauth2-proxy
     * login page and to provide a logout link.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAuthConfigAuthAuthConfigGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/auth-config',
        });
    }
}
