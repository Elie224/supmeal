import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  setAuth: (token: string, user: AuthUser) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        localStorage.setItem("supmeal_token", token);
        localStorage.setItem("supmeal_user", JSON.stringify(user));
        set({ token, user });
      },
      clear: () => {
        localStorage.removeItem("supmeal_token");
        localStorage.removeItem("supmeal_user");
        set({ token: null, user: null });
      },
    }),
    { name: "supmeal-auth" }
  )
);