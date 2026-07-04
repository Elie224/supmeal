import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ChefHat,
  ShieldAlert,
  Trash2,
  UserCheck,
  UserX,
  Search,
} from "lucide-react";
import { api, getCsrfToken } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { cn } from "../lib/utils";

type Tab = "overview" | "users" | "recipes";

interface Stats {
  generated_at: string;
  users: {
    total: number;
    active: number;
    verified: number;
    new_last_7d: number;
    new_last_30d: number;
    by_provider: Record<string, number>;
  };
  recipes: { total: number; public: number };
  cookbooks: { total: number };
  comments: { total: number };
  meal_plans: { total: number };
}

interface AdminUser {
  id: number;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  email: string;
  role: "user" | "admin";
  auth_provider: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  recipe_count: number;
  cookbook_count: number;
}

interface AdminRecipe {
  id: number;
  title: string;
  description: string | null;
  image_url: string | null;
  owner_id: number | null;
  owner_username: string | null;
  cookbook_id: number | null;
  is_public: boolean;
  is_favorite: boolean;
  created_at: string;
}

export default function AdminPage() {
  const me = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("overview");
  const [userSearch, setUserSearch] = useState("");
  const [recipeSearch, setRecipeSearch] = useState("");

  if (me?.role !== "admin") {
    return (
      <div className="card p-8 text-center">
        <ShieldAlert className="w-12 h-12 mx-auto text-red-500 mb-3" />
        <h2 className="text-xl font-semibold text-charcoal-900">Acces refuse</h2>
        <p className="text-sm text-charcoal-500 mt-1">
          Cette page est reservee aux administrateurs.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <header className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-tomato-100 text-tomato-700 flex items-center justify-center">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-display font-semibold text-xl text-charcoal-900">
            Administration
          </h1>
          <p className="text-sm text-charcoal-500">
            Statistiques, gestion des utilisateurs et moderation
          </p>
        </div>
      </header>

      <div className="flex gap-1 border-b border-cream-200">
        {([
          { id: "overview", label: "Vue d ensemble" },
          { id: "users", label: "Utilisateurs" },
          { id: "recipes", label: "Recettes" },
        ] as { id: Tab; label: string }[]).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              tab === t.id
                ? "border-tomato-500 text-tomato-700"
                : "border-transparent text-charcoal-600 hover:text-charcoal-900"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab />}
      {tab === "users" && (
        <UsersTab search={userSearch} setSearch={setUserSearch} qc={qc} />
      )}
      {tab === "recipes" && (
        <RecipesTab search={recipeSearch} setSearch={setRecipeSearch} qc={qc} />
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: number | string;
  hint?: string;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const tones: Record<string, string> = {
    default: "border-cream-200",
    success: "border-green-200 bg-green-50",
    warning: "border-amber-200 bg-amber-50",
    danger: "border-red-200 bg-red-50",
  };
  return (
    <div className={cn("card p-4 border", tones[tone])}>
      <div className="text-xs text-charcoal-500 uppercase tracking-wide">
        {label}
      </div>
      <div className="text-2xl font-display font-bold text-charcoal-900 mt-1">
        {value}
      </div>
      {hint && <div className="text-xs text-charcoal-500 mt-1">{hint}</div>}
    </div>
  );
}

function OverviewTab() {
  const statsQ = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: async () => (await api.get<Stats>("/admin/stats")).data,
    refetchInterval: 30000,
  });

  if (statsQ.isLoading) {
    return <div className="card p-6 text-charcoal-500">Chargement...</div>;
  }
  if (statsQ.isError || !statsQ.data) {
    return (
      <div className="card p-6 text-red-600">
        Erreur lors du chargement des statistiques.
      </div>
    );
  }
  const s = statsQ.data;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Utilisateurs"
          value={s.users.total}
          hint={`${s.users.active} actifs / ${s.users.verified} verifies`}
        />
        <StatCard
          label="Nouveaux (7j)"
          value={s.users.new_last_7d}
          hint={`${s.users.new_last_30d} sur 30 jours`}
        />
        <StatCard label="Recettes" value={s.recipes.total} hint={`${s.recipes.public} publiques`} />
        <StatCard label="Cookbooks" value={s.cookbooks.total} />
        <StatCard label="Commentaires" value={s.comments.total} />
        <StatCard label="Plannings" value={s.meal_plans.total} />
      </div>

      <div className="card p-4">
        <h3 className="font-display font-semibold text-charcoal-900 mb-3">
          Methodes de connexion
        </h3>
        {Object.keys(s.users.by_provider).length === 0 ? (
          <div className="text-sm text-charcoal-500">Aucun utilisateur.</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(s.users.by_provider).map(([provider, count]) => (
              <div
                key={provider}
                className="flex items-center justify-between px-3 py-2 rounded bg-cream-50 border border-cream-200"
              >
                <span className="text-sm text-charcoal-700 capitalize">
                  {provider}
                </span>
                <span className="text-sm font-semibold text-charcoal-900">
                  {count}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="text-xs text-charcoal-500">
        Derniere mise a jour : {new Date(s.generated_at).toLocaleString()}
      </div>
    </div>
  );
}

function UsersTab({
  search,
  setSearch,
  qc,
}: {
  search: string;
  setSearch: (s: string) => void;
  qc: ReturnType<typeof useQueryClient>;
}) {
  const usersQ = useQuery({
    queryKey: ["admin", "users", search],
    queryFn: async () =>
      (await api.get<AdminUser[]>("/admin/users", { params: { q: search || undefined, limit: 100 } }))
        .data,
  });

  const updateRole = useMutation({
    mutationFn: async (vars: { id: number; role: "user" | "admin" }) => {
      const csrf = getCsrfToken();
      return api.patch(`/admin/users/${vars.id}/role`, { role: vars.role }, {
        headers: csrf ? { "X-CSRF-Token": csrf } : {},
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  const updateActive = useMutation({
    mutationFn: async (vars: { id: number; is_active: boolean }) => {
      const csrf = getCsrfToken();
      return api.patch(`/admin/users/${vars.id}/active`, { is_active: vars.is_active }, {
        headers: csrf ? { "X-CSRF-Token": csrf } : {},
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  const deleteU = useMutation({
    mutationFn: async (id: number) => {
      const csrf = getCsrfToken();
      return api.delete(`/admin/users/${id}`, {
        headers: csrf ? { "X-CSRF-Token": csrf } : {},
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });

  return (
    <div className="space-y-3">
      <div className="card p-3 flex items-center gap-2">
        <Search className="w-4 h-4 text-charcoal-500" />
        <input
          className="input flex-1"
          placeholder="Rechercher par email ou nom d utilisateur..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-cream-50 text-charcoal-600">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Utilisateur</th>
              <th className="text-left px-3 py-2 font-medium">Email</th>
              <th className="text-left px-3 py-2 font-medium">Role</th>
              <th className="text-left px-3 py-2 font-medium">Statut</th>
              <th className="text-right px-3 py-2 font-medium">Recettes</th>
              <th className="text-right px-3 py-2 font-medium">Cookbooks</th>
              <th className="text-right px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {usersQ.isLoading && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-charcoal-500">
                  Chargement...
                </td>
              </tr>
            )}
            {usersQ.data?.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-charcoal-500">
                  Aucun utilisateur.
                </td>
              </tr>
            )}
            {usersQ.data?.map((u) => (
              <tr key={u.id} className="border-t border-cream-200">
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-tomato-100 text-tomato-700 text-xs flex items-center justify-center font-semibold">
                      {(u.username || "?").slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-medium text-charcoal-900">
                        {u.full_name || u.username}
                      </div>
                      <div className="text-xs text-charcoal-500">
                        @{u.username} - {u.auth_provider}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-3 py-2 text-charcoal-700">{u.email}</td>
                <td className="px-3 py-2">
                  <select
                    value={u.role}
                    onChange={(e) =>
                      updateRole.mutate({ id: u.id, role: e.target.value as "user" | "admin" })
                    }
                    className="text-xs border border-cream-200 rounded px-2 py-1"
                  >
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td className="px-3 py-2">
                  {u.is_active ? (
                    <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-1 rounded">
                      actif
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-red-700 bg-red-50 px-2 py-1 rounded">
                      desactive
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-charcoal-700">
                  {u.recipe_count}
                </td>
                <td className="px-3 py-2 text-right text-charcoal-700">
                  {u.cookbook_count}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="inline-flex gap-1">
                    <button
                      onClick={() =>
                        updateActive.mutate({ id: u.id, is_active: !u.is_active })
                      }
                      className="btn-outline text-xs px-2 py-1"
                      title={u.is_active ? "Desactiver" : "Activer"}
                    >
                      {u.is_active ? (
                        <UserX className="w-3 h-3" />
                      ) : (
                        <UserCheck className="w-3 h-3" />
                      )}
                    </button>
                    <button
                      onClick={() => {
                        if (
                          window.confirm(
                            `Supprimer definitivement ${u.username} ? Cette action est irreversible.`
                          )
                        ) {
                          deleteU.mutate(u.id);
                        }
                      }}
                      className="btn-outline text-xs px-2 py-1 text-red-600 border-red-200 hover:bg-red-50"
                      title="Supprimer"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecipesTab({
  search,
  setSearch,
  qc,
}: {
  search: string;
  setSearch: (s: string) => void;
  qc: ReturnType<typeof useQueryClient>;
}) {
  const recipesQ = useQuery({
    queryKey: ["admin", "recipes", search],
    queryFn: async () =>
      (
        await api.get<AdminRecipe[]>("/admin/recipes", {
          params: { q: search || undefined, limit: 100 },
        })
      ).data,
  });

  const deleteR = useMutation({
    mutationFn: async (id: number) => {
      const csrf = getCsrfToken();
      return api.delete(`/admin/recipes/${id}`, {
        headers: csrf ? { "X-CSRF-Token": csrf } : {},
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "recipes"] }),
  });

  return (
    <div className="space-y-3">
      <div className="card p-3 flex items-center gap-2">
        <Search className="w-4 h-4 text-charcoal-500" />
        <input
          className="input flex-1"
          placeholder="Rechercher par titre..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-cream-50 text-charcoal-600">
            <tr>
              <th className="text-left px-3 py-2 font-medium">Recette</th>
              <th className="text-left px-3 py-2 font-medium">Auteur</th>
              <th className="text-left px-3 py-2 font-medium">Visibilite</th>
              <th className="text-left px-3 py-2 font-medium">Date</th>
              <th className="text-right px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {recipesQ.isLoading && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-charcoal-500">
                  Chargement...
                </td>
              </tr>
            )}
            {recipesQ.data?.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-charcoal-500">
                  Aucune recette.
                </td>
              </tr>
            )}
            {recipesQ.data?.map((r) => (
              <tr key={r.id} className="border-t border-cream-200">
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    {r.image_url ? (
                      <img
                        src={r.image_url}
                        alt=""
                        className="w-8 h-8 rounded object-cover"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded bg-cream-100 flex items-center justify-center">
                        <ChefHat className="w-4 h-4 text-charcoal-400" />
                      </div>
                    )}
                    <div>
                      <div className="font-medium text-charcoal-900">
                        {r.title}
                      </div>
                      {r.description && (
                        <div className="text-xs text-charcoal-500 line-clamp-1">
                          {r.description}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-3 py-2 text-charcoal-700">
                  {r.owner_username ? `@${r.owner_username}` : "systeme"}
                </td>
                <td className="px-3 py-2">
                  {r.is_public ? (
                    <span className="text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded">
                      publique
                    </span>
                  ) : (
                    <span className="text-xs text-charcoal-600 bg-cream-100 px-2 py-1 rounded">
                      privee
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-charcoal-600 text-xs">
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => {
                      if (
                        window.confirm(
                          `Supprimer la recette "${r.title}" ?`
                        )
                      ) {
                        deleteR.mutate(r.id);
                      }
                    }}
                    className="btn-outline text-xs px-2 py-1 text-red-600 border-red-200 hover:bg-red-50"
                    title="Supprimer"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
