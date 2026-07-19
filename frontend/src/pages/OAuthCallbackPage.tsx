import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { api } from "../lib/api";

export default function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const handled = useRef(false);
  const [showManualFallback, setShowManualFallback] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setShowManualFallback(true), 3000);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    // Nouveau flux securise : on recoit ?code=XXX, on l echange contre un JWT via POST /auth/exchange.
    const code = params.get("code");
    const legacyToken = params.get("token");

    if (code) {
      const fallback = window.setTimeout(() => {
        // Evite un ecran bloque si la requete d echange ne revient pas.
        navigate("/login", { replace: true });
      }, 5000);

      // Echange code -> JWT
      api
        .post("/auth/exchange", { code })
        .then((res) => {
          window.clearTimeout(fallback);
          const token = res.data.access_token;
          const user = res.data.user;
          localStorage.setItem("supmeal_token", token);
          setUser({
            id: user.id,
            email: user.email,
            username: user.username,
            full_name: user.full_name,
            avatar_url: user.avatar_url,
          });
          navigate("/", { replace: true });
        })
        .catch((err) => {
          window.clearTimeout(fallback);
          const status = err?.response?.status as number | undefined;
          if (status === 403) {
            navigate("/login", { replace: true });
            return;
          }

          navigate("/login", { replace: true });
        });
      return;
    }

    // Ancien flux (fallback compatibilite)
    if (legacyToken) {
      localStorage.setItem("supmeal_token", legacyToken);
      api
        .get("/auth/me")
        .then(({ data }) => {
          setUser({
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
  }, [params, navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="text-charcoal-500">Connexion en cours...</div>
        {showManualFallback && (
          <button
            type="button"
            onClick={() => navigate("/login", { replace: true })}
            className="btn-outline text-sm"
          >
            Revenir a la connexion
          </button>
        )}
      </div>
    </div>
  );
}
