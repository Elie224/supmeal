import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { api } from "../lib/api";

export default function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    // Nouveau flux securise : on recoit ?code=XXX, on l echange contre un JWT via POST /auth/exchange.
    const code = params.get("code");
    const legacyToken = params.get("token");

    if (code) {
      // Echange code -> JWT
      api
        .post("/auth/exchange", { code })
        .then((res) => {
          const token = res.data.access_token;
          const user = res.data.user;
          localStorage.setItem("supmeal_token", token);
          setAuth(token, {
            id: user.id,
            email: user.email,
            username: user.username,
            full_name: user.full_name,
            avatar_url: user.avatar_url,
          });
          navigate("/", { replace: true });
        })
        .catch(() => navigate("/login", { replace: true }));
      return;
    }

    // Ancien flux (fallback compatibilite)
    if (legacyToken) {
      localStorage.setItem("supmeal_token", legacyToken);
      api
        .get("/auth/me")
        .then(({ data }) => {
          setAuth(legacyToken, {
            id: data.id,
            email: data.email,
            username: data.username,
            full_name: data.full_name,
            avatar_url: data.avatar_url,
          });
          navigate("/", { replace: true });
        })
        .catch(() => navigate("/login", { replace: true }));
      return;
    }

    navigate("/login", { replace: true });
  }, [params, navigate, setAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-charcoal-500">Connexion en cours...</div>
    </div>
  );
}
