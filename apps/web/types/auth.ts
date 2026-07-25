export interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AuthFormValues {
  email: string;
  password: string;
}
