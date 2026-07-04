import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Upload } from "lucide-react";
import { api } from "../lib/api";
import type { User } from "../lib/types";

export default function SettingsPage() {
  const qc = useQueryClient();
  const [pwd, setPwd] = useState({ current: "", next: "" });
  const [prefs, setPrefs] = useState({
    default_servings: 4,
    dietary_preferences: "",
    allergies: "",
    favorite_cuisines: "",
  });
  const [msg, setMsg] = useState<string | null>(null);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);

  const meQ = useQuery({
    queryKey: ["me"],
    queryFn: async () => (await api.get<User>("/auth/me")).data,
  });

  useEffect(() => {
    if (meQ.data) {
      setPrefs({
        default_servings: meQ.data.default_servings,
        dietary_preferences: meQ.data.dietary_preferences || "",
        allergies: meQ.data.allergies || "",
        favorite_cuisines: meQ.data.favorite_cuisines || "",
      });
    }
  }, [meQ.data]);

  const updatePrefs = useMutation({
    mutationFn: async () => (await api.patch("/users/me", prefs)).data,
    onSuccess: () => {
      setMsg("Preferences enregistrees.");
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });

  const changePwd = useMutation({
    mutationFn: async () =>
      (await api.post("/users/me/change-password", { current_password: pwd.current, new_password: pwd.next })).data,
    onSuccess: () => {
      setMsg("Mot de passe modifie.");
      setPwd({ current: "", next: "" });
    },
    onError: (e: any) => setMsg(e?.response?.data?.detail || "Erreur"),
  });

  const uploadAvatar = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      // Pas de Content-Type ici : axios ajoute automatiquement multipart/form-data avec boundary.
      // L interceptor ajoute X-CSRF-Token depuis le cookie.
      return (await api.post("/users/me/avatar", fd)).data;
    },
    onSuccess: () => {
      setMsg("Avatar mis a jour.");
      setAvatarFile(null);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (e: any) => setMsg(e?.response?.data?.detail || "Erreur upload avatar"),
  });

  const handleExport = async (format: "json" | "csv") => {
    const confirmed = window.confirm(
      "Le fichier exporte contient vos donnees en clair. Voulez-vous continuer ?"
    );
    if (!confirmed) return;
    const res = await api.get(`/import-export/${format}`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `supmeal-export.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (file: File, format: "json" | "csv") => {
    const fd = new FormData();
    fd.append("file", file);
    // Pas de Content-Type explicite : boundary gere par axios + CSRF via interceptor.
    const { data } = await api.post(`/import-export/${format}`, fd);
    setMsg(`Importation : ${data.imported_recipes} recette(s) importee(s).`);
  };

  if (meQ.isLoading || !meQ.data) return <div>Chargement...</div>;

  const oauthUrl = (provider: "google" | "github" | "microsoft") => {
    const base = import.meta.env.VITE_API_URL || "/api/v1";
    return `${base}/auth/oauth/${provider}/login`;
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="font-display font-bold text-2xl text-charcoal-900">Parametres</h1>
      {msg && <div className="card p-3 text-sm text-charcoal-700 bg-cream-100">{msg}</div>}

      <section className="card p-5 space-y-3">
        <h2 className="font-display font-semibold text-lg">Profil</h2>
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-cream-100 overflow-hidden flex items-center justify-center">
            {meQ.data.avatar_url ? (
              <img src={meQ.data.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <span className="text-charcoal-500 text-sm">N/A</span>
            )}
          </div>
          <div className="space-y-2">
            <label className="btn-outline cursor-pointer text-xs">
              Choisir un avatar
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                hidden
                onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
              />
            </label>
            <button
              type="button"
              className="btn-primary text-xs"
              disabled={!avatarFile || uploadAvatar.isPending}
              onClick={() => avatarFile && uploadAvatar.mutate(avatarFile)}
            >
              {uploadAvatar.isPending ? "Upload..." : "Uploader"}
            </button>
          </div>
        </div>
        <div>
          <label className="label">Nom d'utilisateur</label>
          <input className="input" disabled value={meQ.data.username} />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" disabled value={meQ.data.email} />
        </div>
      </section>

      <section className="card p-5 space-y-3">
        <h2 className="font-display font-semibold text-lg">Securite</h2>
        <form onSubmit={(e) => { e.preventDefault(); changePwd.mutate(); }} className="space-y-3">
          <div>
            <label className="label">Mot de passe actuel</label>
            <input type="password" className="input" value={pwd.current} onChange={(e) => setPwd({ ...pwd, current: e.target.value })} />
          </div>
          <div>
            <label className="label">Nouveau mot de passe</label>
            <input type="password" className="input" minLength={8} value={pwd.next} onChange={(e) => setPwd({ ...pwd, next: e.target.value })} />
          </div>
          <button type="submit" className="btn-primary" disabled={!pwd.current || !pwd.next}>Changer le mot de passe</button>
        </form>
        <div className="border-t border-cream-200 pt-3">
          <p className="text-sm text-charcoal-500 mb-2">
            Lier un provider OAuth: si le compte provider utilise le meme email, il sera associe.
          </p>
          <div className="flex gap-2">
            <a href={oauthUrl("google")} className="btn-outline text-xs">Lier Google</a>
            <a href={oauthUrl("github")} className="btn-outline text-xs">Lier GitHub</a>
            <a href={oauthUrl("microsoft")} className="btn-outline text-xs">Lier Microsoft</a>
          </div>
        </div>
      </section>

      <section className="card p-5 space-y-3">
        <h2 className="font-display font-semibold text-lg">Preferences culinaires</h2>
        <div>
          <label className="label">Portions par defaut</label>
          <input type="number" min={1} max={50} className="input" value={prefs.default_servings} onChange={(e) => setPrefs({ ...prefs, default_servings: +e.target.value })} />
        </div>
        <div>
          <label className="label">Regime alimentaire</label>
          <input className="input" placeholder="vegetarien, sans gluten..." value={prefs.dietary_preferences} onChange={(e) => setPrefs({ ...prefs, dietary_preferences: e.target.value })} />
        </div>
        <div>
          <label className="label">Allergies (separees par virgule)</label>
          <input className="input" placeholder="gluten, lactose, fruits a coque..." value={prefs.allergies} onChange={(e) => setPrefs({ ...prefs, allergies: e.target.value })} />
        </div>
        <div>
          <label className="label">Types de cuisine preferes</label>
          <input className="input" placeholder="francaise, italienne, asiatique..." value={prefs.favorite_cuisines} onChange={(e) => setPrefs({ ...prefs, favorite_cuisines: e.target.value })} />
        </div>
        <button onClick={() => updatePrefs.mutate()} className="btn-primary">Enregistrer</button>
      </section>

      <section className="card p-5 space-y-3">
        <h2 className="font-display font-semibold text-lg">Donnees</h2>
        <p className="text-sm text-charcoal-500">Vos donnees sont en clair dans le fichier exporte. Ne partagez pas ce fichier publiquement.</p>
        <div className="flex gap-2">
          <button onClick={() => handleExport("json")} className="btn-outline">
            <Download className="w-4 h-4" /> Exporter JSON
          </button>
          <button onClick={() => handleExport("csv")} className="btn-outline">
            <Download className="w-4 h-4" /> Exporter CSV
          </button>
        </div>
        <div className="border-t border-cream-200 pt-3">
          <label className="label">Importer</label>
          <div className="flex gap-2">
            <label className="btn-outline cursor-pointer">
              <Upload className="w-4 h-4" /> Importer JSON
              <input type="file" accept=".json" hidden onChange={(e) => e.target.files?.[0] && handleImport(e.target.files[0], "json")} />
            </label>
            <label className="btn-outline cursor-pointer">
              <Upload className="w-4 h-4" /> Importer CSV
              <input type="file" accept=".csv" hidden onChange={(e) => e.target.files?.[0] && handleImport(e.target.files[0], "csv")} />
            </label>
          </div>
        </div>
      </section>
    </div>
  );
}
