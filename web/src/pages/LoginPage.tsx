import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChefHat } from "lucide-react";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      setAuth(data.access_token, {
        id: data.user.id,
        email: data.user.email,
        username: data.user.username,
        full_name: data.user.full_name,
        avatar_url: data.user.avatar_url,
      });
      navigate("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Connexion impossible");
    } finally {
      setLoading(false);
    }
  };

  const oauthUrl = (provider: string) => {
    const base = import.meta.env.VITE_API_URL || "/api/v1";
    return `${base}/auth/oauth/${provider}/login`;
  };

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
          <div className="grid grid-cols-3 gap-2">
            <a href={oauthUrl("google")} className="btn-outline text-xs">Google</a>
            <a href={oauthUrl("github")} className="btn-outline text-xs">GitHub</a>
            <a href={oauthUrl("microsoft")} className="btn-outline text-xs">Microsoft</a>
          </div>
          <div className="text-center text-sm text-charcoal-500 pt-2 space-y-1">
            <div>Pas encore de compte ? <Link to="/register" className="text-tomato-600 hover:underline">Creer un compte</Link></div>
          </div>
        </form>
      </div>
    </div>
  );
}