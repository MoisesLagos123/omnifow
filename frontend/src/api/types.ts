export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthUser {
  id: string;
  nombre: string;
  email: string;
  rut?: string;
}

export interface SucursalPermitida {
  id: string;
  codigo: string;
  nombre: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: AuthUser;
  perfiles: string[];
  permisos: string[];
  /**
   * Sucursales en las que el usuario puede operar. Lista vacía = acceso a todas
   * (modo Sysadmin / sin restricción). El campo puede no venir en versiones
   * antiguas del backend, por eso es opcional al deserializar.
   */
  sucursales_permitidas?: SucursalPermitida[];
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

export interface ApiErrorEnvelope {
  error: ApiErrorPayload;
}
