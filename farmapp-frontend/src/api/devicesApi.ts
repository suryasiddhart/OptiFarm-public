import axiosInstance from "./axiosInstance";
import type { Device, DeviceCreatePayload, DeviceCredentials } from "../types";

export const devicesApi = {
  // Active devices of the user, or of one field
  list: async (fieldId?: number): Promise<Device[]> => {
    const response = await axiosInstance.get<Device[]>("/devices/", {
      params: fieldId === undefined ? {} : { fieldid: fieldId },
    });
    return response.data;
  },

  // The response carries the passkey: show it once, never store it
  create: async (payload: DeviceCreatePayload): Promise<DeviceCredentials> => {
    const response = await axiosInstance.post<DeviceCredentials>("/devices/", payload);
    return response.data;
  },

  rotatePasskey: async (deviceId: string): Promise<DeviceCredentials> => {
    const response = await axiosInstance.post<DeviceCredentials>(
      `/devices/${encodeURIComponent(deviceId)}/rotate-passkey`
    );
    return response.data;
  },

  // Disables the device: its MQTT login stops working immediately
  remove: async (deviceId: string): Promise<Device> => {
    const response = await axiosInstance.delete<Device>(
      `/devices/${encodeURIComponent(deviceId)}`
    );
    return response.data;
  },
};
