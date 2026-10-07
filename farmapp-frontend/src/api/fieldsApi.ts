import axiosInstance from "./axiosInstance";
import type { Field, FieldCreatePayload } from "../types";

export const fieldsApi = {
  create: async (payload: FieldCreatePayload): Promise<Field> => {
    const response = await axiosInstance.post<Field>("/fields/", payload);
    return response.data;
  },

  list: async (): Promise<Field[]> => {
    const response = await axiosInstance.get<Field[]>("/fields/");
    return response.data;
  },

  getById: async (fieldId: number): Promise<Field> => {
    const response = await axiosInstance.get<Field>(`/fields/${fieldId}`);
    return response.data;
  },
};
