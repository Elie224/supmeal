import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { api } from "../lib/api";

export default function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      navigate("/login");
      return;
    }
    localStorage.setItem("supmeal_token", token);
    api.get("/auth/me")
      .then(({ data }) => {
        setAuth(token, {
          id: data.id,
          email: data.email,
          username: data.username,
          full_name: data.full_name,
          avatar_url: data.avatar_url,
        });
        navigate("/");
      })
      .catch(() => navigate("/login"));
  }, [params, navigate, setAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-charcoal-500">Connexion en cours...</div>
    </div>
  );
}