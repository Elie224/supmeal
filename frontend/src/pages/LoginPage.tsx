import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ChefHat } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

type OAuthProviders = {
  google: boolean;
  github: boolean;
};

export default function LoginPage() {
  const [params] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const from = (location.state as { from?: string } | null)?.from || "/";

  useEffect(() => {
    const verified = params.get("verified");
    const qEmail = params.get("email");
    if (qEmail) {
      setEmail(qEmail);
    }
    if (verified === "1") {
      setInfo("Email verifie. Vous pouvez maintenant vous connecter.");
    }
  }, [params]);

  const oauthProvidersQ = useQuery({
    queryKey: ["oauth-providers"],
    queryFn: async () => (await api.get<OAuthProviders>("/auth/oauth/providers")).data,
    retry: false,
  });

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      setUser({
        id: data.user.id,
        email: data.user.email,
        username: data.user.username,
        full_name: data.user.full_name,
        avatar_url: data.user.avatar_url,
      });
      navigate(from, { replace: true });
    } catch (err: any) {
      const detail = err?.response?.data?.detail as string | undefined;
      setError(detail || "Connexion impossible");
    } finally {
      setLoading(false);
    }
  };

  const oauthUrl = (provider: string) => {
    const base = import.meta.env.VITE_API_URL || "/api/v1";
    return `${base}/auth/oauth/${provider}/login`;
  };

  const providerButtons = [
    { key: "google", label: "Google" },
    { key: "github", label: "GitHub" },
  ] as const;

  const enabledProviders = providerButtons.filter((p) => oauthProvidersQ.data?.[p.key]);

  return (
    <div className="min-h-screen bg-cream-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex w-14 h-14 rounded-full bg-tomato-500 items-center justify-center mb-3">
            <ChefHat className="w-7 h-7 text-cream-50" />
          </div>
          <h1 className="font-display font-bold text-3xl text-charcoal-900">SUPMEAL</h1>
          <p className="text-charcoal-500 mt-1">Cuisinez, partagez, savourez.</p>
        </div>

        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          {info && (
            <div className="rounded bg-green-50 border border-green-200 text-green-700 text-sm p-3">{info}</div>
          )}
          {error && (
            <div className="rounded bg-red-50 border border-red-200 text-red-700 text-sm p-3">{error}</div>
          )}
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input" />
          </div>
          <div>
            <label className="label" htmlFor="password">Mot de passe</label>
            <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="input" />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Connexion..." : "Se connecter"}
          </button>
          <div className="text-center text-sm text-charcoal-500">ou continuer avec</div>
          {enabledProviders.length > 0 ? (
            <div className="w-full flex items-center justify-center gap-3 translate-x-2">
              {enabledProviders.map((provider) => (
                <a key={provider.key} href={oauthUrl(provider.key)} className="btn-outline text-xs w-36 justify-center">
                  {provider.label}
                </a>
              ))}
            </div>
          ) : (
            <div className="text-center text-xs text-charcoal-500">
              Connexion OAuth non configuree sur cet environnement.
            </div>
          )}
          <div className="text-center text-sm text-charcoal-500 pt-2">
            Pas encore de compte ? <Link to="/register" className="text-tomato-600 hover:underline">Creer un compte</Link>
          </div>
        </form>
      </div>
    </div>
  );
}