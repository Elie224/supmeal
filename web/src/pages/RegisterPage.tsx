import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChefHat } from "lucide-react";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    full_name: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      setAuth(data.access_token, {
        id: data.user.id,
        email: data.user.email,
        username: data.user.username,
        full_name: data.user.full_name,
        avatar_url: data.user.avatar_url,
      });
      navigate("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Inscription impossible");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-cream-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex w-14 h-14 rounded-full bg-tomato-500 items-center justify-center mb-3">
            <ChefHat className="w-7 h-7 text-cream-50" />
          </div>
          <h1 className="font-display font-bold text-3xl text-charcoal-900">Creer un compte</h1>
        </div>
        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          {error && (
            <div className="rounded bg-red-50 border border-red-200 text-red-700 text-sm p-3">{error}</div>
          )}
          <div>
            <label className="label">Nom complet (optionnel)</label>
            <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div>
            <label className="label">Nom d'utilisateur</label>
            <input className="input" required minLength={3} pattern="[a-zA-Z0-9_.\-]+" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          </div>
          <div>
            <label className="label">Email</label>
            <input type="email" className="input" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <label className="label">Mot de passe (8 caracteres minimum)</label>
            <input type="password" className="input" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Creation..." : "Creer mon compte"}
          </button>
          <div className="text-center text-sm text-charcoal-500">
            Deja un compte ? <Link to="/login" className="text-tomato-600 hover:underline">Se connecter</Link>
          </div>
        </form>
      </div>
    </div>
  );
}