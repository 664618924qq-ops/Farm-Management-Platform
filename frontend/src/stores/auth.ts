import { defineStore } from "pinia";

import { loginRequest, setAuthToken, type AuthUser } from "../api/client";

type AuthState = {
  token: string | null;
  user: AuthUser | null;
};

const TOKEN_KEY = "livestock-monitor-token";
const USER_KEY = "livestock-monitor-user";

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    token: localStorage.getItem(TOKEN_KEY),
    user: JSON.parse(localStorage.getItem(USER_KEY) ?? "null") as AuthUser | null
  }),
  actions: {
    async login(username: string, password: string) {
      const result = await loginRequest(username, password);
      this.token = result.token;
      this.user = result.user;
      localStorage.setItem(TOKEN_KEY, result.token);
      localStorage.setItem(USER_KEY, JSON.stringify(result.user));
      setAuthToken(result.token);
      return result;
    },
    hydrate() {
      if (this.token) {
        setAuthToken(this.token);
      }
    },
    logout() {
      this.token = null;
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      setAuthToken(null);
    }
  }
});
