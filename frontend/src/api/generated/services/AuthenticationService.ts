/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { OAuthCallbackRequest } from '../models/OAuthCallbackRequest';
import type { TokenResponse } from '../models/TokenResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthenticationService {
    /**
     * Oauth Callback
     * Handle OAuth callback and exchange code for tokens.
     * @param requestBody
     * @returns TokenResponse Successful Response
     * @throws ApiError
     */
    public static oauthCallbackAuthOauthCallbackPost(
        requestBody: OAuthCallbackRequest,
    ): CancelablePromise<TokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/oauth/callback',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Refresh Token
     * Refresh access token using refresh token.
     * @param refreshToken
     * @returns any Successful Response
     * @throws ApiError
     */
    public static refreshTokenAuthRefreshPost(
        refreshToken: string,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/refresh',
            query: {
                'refresh_token': refreshToken,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Current User Info
     * Get current user information.
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
     * Get authentication configuration for frontend.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getAuthConfigAuthAuthConfigGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/auth-config',
        });
    }
}
