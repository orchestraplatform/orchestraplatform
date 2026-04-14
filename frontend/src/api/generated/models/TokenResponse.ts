/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Token response model.
 */
export type TokenResponse = {
    access_token: string;
    refresh_token: string;
    token_type?: string;
    expires_in: number;
    user: Record<string, any>;
};

