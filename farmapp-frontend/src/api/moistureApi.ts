import axiosInstance from "./axiosInstance";
import type { MoistureReading } from "../types";

export const moistureApi = {
  getByField: async (
    fieldId: number,
    limit: number = 1000
  ): Promise<MoistureReading[]> => {
    const response = await axiosInstance.get<MoistureReading[]>(
      `/moisture/field/${fieldId}`,
      { params: { limit } }
    );
    return response.data;
  },
};
