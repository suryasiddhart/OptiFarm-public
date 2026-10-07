import axiosInstance from "./axiosInstance";
import type {
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  LogoutResponse,
  User,
} from "../types";

export const authApi = {
  register: async (payload: RegisterPayload): Promise<User> => {
    const response = await axiosInstance.post<User>("/auth/register", payload);
    return response.data;
  },

  login: async (payload: LoginPayload): Promise<TokenResponse> => {
    const response = await axiosInstance.post<TokenResponse>(
      "/auth/login",
      payload
    );
    return response.data;
  },

  logout: async (): Promise<LogoutResponse> => {
    const response = await axiosInstance.post<LogoutResponse>("/auth/logout");
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await axiosInstance.get<User>("/users/me");
    return response.data;
  },
};
