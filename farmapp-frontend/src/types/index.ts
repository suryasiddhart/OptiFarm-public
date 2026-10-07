// ─── Auth Types ──────────────────────────────────────────────────────────────

export interface User {
  userid: number;
  firstname: string;
  lastname: string;
  mobileno: string;
  emailid: string | null;
  activationstatus: boolean;
}

export interface LoginPayload {
  mobileno: string;
  password: string;
}

export interface RegisterPayload {
  firstname: string;
  lastname: string;
  mobileno: string;
  emailid?: string;
  password?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LogoutResponse {
  message: string;
  userid: number;
}

// ─── Field Types ─────────────────────────────────────────────────────────────

export interface FieldCreatePayload {
  fieldlength: number;
  fieldbreadth: number;
  croptype: string;
  cropsubtype: string;
  cropinterval: number;
  fieldlat: number;
  fieldlong: number;
  soildata?: Record<string, unknown>;
  labels?: Record<string, unknown>;
}

export interface Field {
  fieldid: number;
  userid: number;
  fieldlength: number;
  fieldbreadth: number;
  croptype: string;
  cropsubtype: string;
  cropinterval: number;
  fieldlat: number;
  fieldlong: number;
  soildata: Record<string, unknown> | null;
  labels: Record<string, unknown> | null;
  inference: Record<string, unknown> | null;
}

// ─── Moisture Types ──────────────────────────────────────────────────────────

export interface MoistureReading {
  moisture: number;
  rtctime: string;
  deviceid: string;
  userinfo: number;
  fieldid: number | null;
}

// ─── Grid / Heatmap Types ────────────────────────────────────────────────────

export interface GridCell {
  row: number;
  col: number;
  moisture: number | null;
  deviceid: string | null;
  timestamp: string | null;
}

export interface SensorGrid {
  rows: number;
  cols: number;
  cells: GridCell[][];
}
