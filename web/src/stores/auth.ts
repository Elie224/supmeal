import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "../lib/api";

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
}

interface AuthState {
  // Le token JWT est maintenant en cookie httpOnly (defense XSS).
  // On garde un flag isAuthenticated + le user dans le store.
  isAuthenticated: boolean;
  user: AuthUser | null;
  setUser: (user: AuthUser) => void;
  clear: () => void;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      setUser: (user) => {
        localStorage.setItem("supmeal_user", JSON.stringify(user));
        set({ isAuthenticated: true, user });
      },
      clear: () => {
        localStorage.removeItem("supmeal_user");
        localStorage.removeItem("supmeal_token");
        set({ isAuthenticated: false, user: null });
      },
      hydrate: async () => {
        // Au demarrage, on verifie si on a un cookie valide via /auth/me.
        // Si oui, on recupere le user. Sinon, on clear.
        try {
          const { data } = await api.get("/auth/me");
          set({
            isAuthenticated: true,
            user: {
              id: data.id,
              email: data.email,
              username: data.username,
              full_name: data.full_name,
              avatar_url: data.avatar_url,
            },
          });
          localStorage.setItem("supmeal_user", JSON.stringify(data));
        } catch {
          set({ isAuthenticated: false, user: null });
        }
      },
    }),
    {
      name: "supmeal-auth",
      partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated }),
    }
  )
);
