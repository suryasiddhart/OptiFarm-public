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
  // One value per grid cell, keyed m<row>_<col> (1-based), e.g. { m1_1: 31.4 }.
  // null for readings stored before the grid format.
  moisture: Record<string, number> | null;
  rtctime: string;
  deviceid: string;
  userinfo: number;
  fieldid: number | null;
}

// ─── Device Types ────────────────────────────────────────────────────────────

export interface Device {
  deviceid: string; // generated; also the MQTT username
  devicename: string; // display name chosen by the user
  userinfo: number;
  fieldid: number | null;
  status: "active" | "disabled";
  last_seen: string | null;
  created_at: string;
}

// Returned only by create and rotate-passkey: the passkey is never stored
export interface DeviceCredentials extends Device {
  passkey: string; // MQTT password
  mqtt_topic: string;
}

export interface DeviceCreatePayload {
  devicename: string;
  fieldid: number;
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
