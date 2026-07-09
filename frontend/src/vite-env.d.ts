/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  /** GA4 measurement ID (local-dev only; production uses runtime config.js). Unset = analytics off. */
  readonly VITE_GA_MEASUREMENT_ID?: string
  // more env variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
