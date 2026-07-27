export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// Kept in sync with the backend enums (schemas/auth.py). `value` is what the
// API stores; `label` is what the user sees.
export const REFERRAL_SOURCES = [
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "twitter", label: "X (Twitter)" },
  { value: "youtube", label: "YouTube" },
  { value: "google_search", label: "Google Search" },
  { value: "friend", label: "Friend or colleague" },
  { value: "blog", label: "Blog or article" },
  { value: "other", label: "Other" },
] as const;

export const USE_PURPOSES = [
  { value: "professional", label: "Professional / work" },
  { value: "educational", label: "Educational / student" },
  { value: "research", label: "Research" },
  { value: "personal", label: "Personal / for fun" },
  { value: "business", label: "Business / startup" },
  { value: "other", label: "Other" },
] as const;

// Login reads only email + password; the rest are collected at registration.
export interface AuthFormValues {
  email: string;
  password: string;
  full_name?: string;
  referral_source?: string;
  referral_source_other?: string;
  use_purpose?: string;
  marketing_opt_in?: boolean;
  signup_metadata?: Record<string, string>;
}
