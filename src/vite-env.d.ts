/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_URL?: string;
  readonly VITE_USER_AUTH_REQUIRED?: string;
}
interface ImportMeta { readonly env: ImportMetaEnv; }
