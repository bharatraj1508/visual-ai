// Client-side upload cap — a UX guard so oversized files are refused instantly
// instead of after a wasted upload. The backend enforces the real limit; keep
// this in sync with the API's MAX_UPLOAD_MB (default 50).
export const MAX_UPLOAD_MB = Number(
  process.env.NEXT_PUBLIC_MAX_UPLOAD_MB ?? 50,
);

export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;
