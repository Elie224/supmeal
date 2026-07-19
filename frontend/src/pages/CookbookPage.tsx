import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Send, Trash2, UserPlus } from "lucide-react";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import RecipeCard from "../components/RecipeCard";
import type { Cookbook, Message, Recipe, Tag } from "../lib/types";

type Tab = "recipes" | "members" | "discussion" | "settings";

export default function CookbookPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [tab, setTab] = useState<Tab>("recipes");
  const [search, setSearch] = useState("");
  const [ingredient, setIngredient] = useState("");
  const [maxPrep, setMaxPrep] = useState<number | "">("");
  const [favOnly, setFavOnly] = useState(false);
  const [tagFilter, setTagFilter] = useState<number | null>(null);
  const [tagCategoryFilter, setTagCategoryFilter] = useState<string>("");
  const [msgContent, setMsgContent] = useState("");
  const [newMember, setNewMember] = useState({ email: "", role: "reader" });
  const [showCreateRecipe, setShowCreateRecipe] = useState(false);
  const [newRecipe, setNewRecipe] = useState({
    title: "",
    description: "",
    prep_time_minutes: 0,
    cook_time_minutes: 0,
    servings: 4,
    ingredients: [""],
    steps: [""],
  });
  const [settingsForm, setSettingsForm] = useState({ name: "", description: "" });
  const wsRef = useRef<WebSocket | null>(null);
  const [liveMessages, setLiveMessages] = useState<Message[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  const cookbookQ = useQuery({
    queryKey: ["cookbook", id],
    queryFn: async () => (await api.get<Cookbook>(`/cookbooks/${id}`)).data,
    enabled: !!id,
  });

  const recipesQ = useQuery({
    queryKey: ["cookbook-recipes", id, search, ingredient, maxPrep, favOnly, tagFilter, tagCategoryFilter],
    queryFn: async () => {
      const params: Record<string, unknown> = {
        search: search || undefined,
        ingredient: ingredient || undefined,
        max_prep_time: maxPrep === "" ? undefined : maxPrep,
        favorites_only: favOnly || undefined,
        tag_ids: tagFilter ? [tagFilter] : undefined,
        tag_category: tagCategoryFilter || undefined,
      };
      return (await api.get<Recipe[]>(`/cookbooks/${id}/recipes`, { params })).data;
    },
    enabled: !!id && tab === "recipes",
  });

  const tagsQ = useQuery({
    queryKey: ["tags"],
    queryFn: async () => (await api.get<Tag[]>("/tags")).data,
    enabled: tab === "recipes",
  });

  const messagesQ = useQuery({
    queryKey: ["cookbook-messages", id],
    queryFn: async () => (await api.get<Message[]>(`/cookbooks/${id}/messages`)).data,
    enabled: !!id && tab === "discussion",
    // Fallback robuste si le WebSocket est indisponible.
    refetchInterval: tab === "discussion" ? 4000 : false,
  });

  useEffect(() => {
    if (tab === "discussion" && id) {
      const token = localStorage.getItem("supmeal_token");
      const apiBase = import.meta.env.VITE_API_URL || "/api/v1";
      const wsBase = apiBase.startsWith("http")
        ? apiBase.replace(/^http/, "ws")
        : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}${apiBase}`;
      const wsUrl = `${wsBase}/cookbooks/${id}/ws`;
      const ws = token ? new WebSocket(wsUrl, [`bearer.${token}`]) : new WebSocket(wsUrl);
      ws.onopen = () => setWsConnected(true);
      ws.onerror = () => setWsConnected(false);
      ws.onclose = () => setWsConnected(false);
      ws.onmessage = (ev) => {
        const msg: Message = JSON.parse(ev.data);
        setLiveMessages((prev) => [...prev, msg]);
      };
      wsRef.current = ws;
      return () => {
        ws.close();
        setWsConnected(false);
      };
    }
  }, [tab, id]);

  useEffect(() => {
    if (cookbookQ.data) {
      setSettingsForm({
        name: cookbookQ.data.name,
        description: cookbookQ.data.description || "",
      });
    }
  }, [cookbookQ.data]);

  const sendMessage = useMutation({
    mutationFn: async (content: string) => (await api.post(`/cookbooks/${id}/messages`, { content })).data,
  });

  const addMember = useMutation({
    mutationFn: async () => (await api.post(`/cookbooks/${id}/members`, { user_email: newMember.email, role: newMember.role })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cookbook", id] });
      setNewMember({ email: "", role: "reader" });
    },
  });

  const updateMemberRole = useMutation({
    mutationFn: async (payload: { userId: number; role: string }) =>
      (await api.patch(`/cookbooks/${id}/members/${payload.userId}`, { role: payload.role })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cookbook", id] }),
  });

  const removeMember = useMutation({
    mutationFn: async (userId: number) => (await api.delete(`/cookbooks/${id}/members/${userId}`)).data,
    onSuccess: (_data, userId) => {
      if (userId === user?.id) {
        navigate("/cookbooks");
        return;
      }
      qc.invalidateQueries({ queryKey: ["cookbook", id] });
    },
  });

  const createRecipe = useMutation({
    mutationFn: async () => {
      const payload = {
        title: newRecipe.title,
        description: newRecipe.description || null,
        prep_time_minutes: newRecipe.prep_time_minutes,
        cook_time_minutes: newRecipe.cook_time_minutes,
        servings: newRecipe.servings,
        ingredients: newRecipe.ingredients
          .filter((name) => name.trim())
          .map((name, idx) => ({ name, position: idx })),
        steps: newRecipe.steps
          .filter((content) => content.trim())
          .map((content, idx) => ({ content, position: idx })),
      };
      return (await api.post(`/cookbooks/${id}/recipes`, payload)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cookbook-recipes", id] });
      setShowCreateRecipe(false);
      setNewRecipe({
        title: "",
        description: "",
        prep_time_minutes: 0,
        cook_time_minutes: 0,
        servings: 4,
        ingredients: [""],
        steps: [""],
      });
    },
  });

  const updateCookbook = useMutation({
    mutationFn: async () =>
      (await api.patch(`/cookbooks/${id}`, {
        name: settingsForm.name,
        description: settingsForm.description || null,
      })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cookbook", id] }),
  });

  const deleteCookbook = useMutation({
    mutationFn: async () => (await api.delete(`/cookbooks/${id}`)).data,
    onSuccess: () => navigate("/cookbooks"),
  });

  if (cookbookQ.isLoading) return <div>Chargement...</div>;
  if (!cookbookQ.data) return <div>Cookbook introuvable</div>;

  const cb = cookbookQ.data;
  const myMember = cb.members.find((m) => m.user.id === user?.id);
  const myRole = myMember?.role;
  const canDiscuss = !!myRole;
  const isCreator = myRole === "creator";
  const canEditRecipes = myRole === "creator" || myRole === "editor";

  const allMessages = [...(messagesQ.data || []), ...liveMessages];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/cookbooks" className="text-xs text-charcoal-500 hover:underline">Mes cookbooks</Link>
          <h1 className="font-display font-bold text-2xl text-charcoal-900 mt-1">{cb.name}</h1>
          {cb.description && <p className="text-sm text-charcoal-500 mt-1">{cb.description}</p>}
        </div>
      </div>

      <div className="border-b border-cream-200 flex gap-1">
        {(["recipes", "members", "discussion", "settings"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t ? "border-tomato-500 text-tomato-700" : "border-transparent text-charcoal-500"}`}
          >
            {t === "recipes" && "Recettes"}
            {t === "members" && "Membres"}
            {t === "discussion" && "Discussion"}
            {t === "settings" && "Parametres"}
          </button>
        ))}
      </div>

      {tab === "recipes" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-2">
            <div className="relative md:col-span-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-500" />
              <input className="input pl-9" placeholder="Recherche plein texte" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <input className="input" placeholder="Ingredient" value={ingredient} onChange={(e) => setIngredient(e.target.value)} />
            <input
              className="input"
              type="number"
              min={0}
              placeholder="Prep max (min)"
              value={maxPrep}
              onChange={(e) => setMaxPrep(e.target.value ? Number(e.target.value) : "")}
            />
            <button type="button" className="btn-outline" onClick={() => setFavOnly((v) => !v)}>
              {favOnly ? "Favoris: ON" : "Favoris: OFF"}
            </button>
            <select
              className="input"
              value={tagCategoryFilter}
              onChange={(e) => setTagCategoryFilter(e.target.value)}
            >
              <option value="">Toutes categories</option>
              {Array.from(new Set((tagsQ.data || []).map((t) => t.category).filter(Boolean))).map((category) => (
                <option key={category as string} value={category as string}>{category as string}</option>
              ))}
            </select>
          </div>

          {tagsQ.data && tagsQ.data.length > 0 && (
            <div className="flex flex-wrap gap-2">
              <button type="button" className={`badge ${tagFilter === null ? "bg-tomato-500 text-cream-50" : ""}`} onClick={() => setTagFilter(null)}>
                Tous les tags
              </button>
              {tagsQ.data.map((t) => (
                <button
                  type="button"
                  key={t.id}
                  className={`badge ${tagFilter === t.id ? "bg-tomato-500 text-cream-50" : ""}`}
                  onClick={() => setTagFilter((prev) => (prev === t.id ? null : t.id))}
                >
                  {t.name}
                </button>
              ))}
            </div>
          )}

          {canEditRecipes && (
            <div className="card p-4 space-y-3">
              <button type="button" className="btn-primary" onClick={() => setShowCreateRecipe((v) => !v)}>
                <Plus className="w-4 h-4" /> Ajouter une recette au cookbook
              </button>
              {showCreateRecipe && (
                <form onSubmit={(e) => { e.preventDefault(); createRecipe.mutate(); }} className="space-y-3">
                  <input
                    className="input"
                    placeholder="Titre"
                    value={newRecipe.title}
                    onChange={(e) => setNewRecipe({ ...newRecipe, title: e.target.value })}
                    required
                  />
                  <textarea
                    className="input"
                    rows={2}
                    placeholder="Description"
                    value={newRecipe.description}
                    onChange={(e) => setNewRecipe({ ...newRecipe, description: e.target.value })}
                  />
                  <div className="grid grid-cols-3 gap-2">
                    <input
                      className="input"
                      type="number"
                      min={0}
                      value={newRecipe.prep_time_minutes}
                      onChange={(e) => setNewRecipe({ ...newRecipe, prep_time_minutes: Number(e.target.value) || 0 })}
                      placeholder="Prep"
                    />
                    <input
                      className="input"
                      type="number"
                      min={0}
                      value={newRecipe.cook_time_minutes}
                      onChange={(e) => setNewRecipe({ ...newRecipe, cook_time_minutes: Number(e.target.value) || 0 })}
                      placeholder="Cuisson"
                    />
                    <input
                      className="input"
                      type="number"
                      min={1}
                      value={newRecipe.servings}
                      onChange={(e) => setNewRecipe({ ...newRecipe, servings: Number(e.target.value) || 1 })}
                      placeholder="Portions"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="label !mb-0">Ingredients</label>
                    {newRecipe.ingredients.map((ing, idx) => (
                      <input
                        key={idx}
                        className="input"
                        placeholder={`Ingredient ${idx + 1}`}
                        value={ing}
                        onChange={(e) => {
                          const next = [...newRecipe.ingredients];
                          next[idx] = e.target.value;
                          setNewRecipe({ ...newRecipe, ingredients: next });
                        }}
                      />
                    ))}
                    <button
                      type="button"
                      className="btn-outline"
                      onClick={() => setNewRecipe({ ...newRecipe, ingredients: [...newRecipe.ingredients, ""] })}
                    >
                      + Ingredient
                    </button>
                  </div>
                  <div className="space-y-2">
                    <label className="label !mb-0">Etapes</label>
                    {newRecipe.steps.map((step, idx) => (
                      <textarea
                        key={idx}
                        className="input"
                        rows={2}
                        placeholder={`Etape ${idx + 1}`}
                        value={step}
                        onChange={(e) => {
                          const next = [...newRecipe.steps];
                          next[idx] = e.target.value;
                          setNewRecipe({ ...newRecipe, steps: next });
                        }}
                      />
                    ))}
                    <button
                      type="button"
                      className="btn-outline"
                      onClick={() => setNewRecipe({ ...newRecipe, steps: [...newRecipe.steps, ""] })}
                    >
                      + Etape
                    </button>
                  </div>
                  <button type="submit" className="btn-primary" disabled={createRecipe.isPending}>
                    {createRecipe.isPending ? "Creation..." : "Creer dans le cookbook"}
                  </button>
                </form>
              )}
            </div>
          )}

          <div className="relative">
          </div>
          {recipesQ.data && recipesQ.data.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {recipesQ.data.map((r) => <RecipeCard key={r.id} recipe={r} />)}
            </div>
          ) : (
            <div className="card p-8 text-center text-charcoal-500 text-sm">Aucune recette dans ce cookbook.</div>
          )}
        </div>
      )}

      {tab === "members" && (
        <div className="space-y-4">
          <div className="card p-4">
            <h3 className="font-display font-semibold mb-3">Membres ({cb.members.length})</h3>
            <div className="space-y-2">
              {cb.members.map((m) => (
                <div key={m.id} className="flex items-center justify-between py-2 border-b border-cream-200 last:border-0">
                  <div>
                    <div className="text-sm font-medium text-charcoal-900">{m.user.full_name || m.user.username}</div>
                    <div className="text-xs text-charcoal-500">{m.user.username}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isCreator && m.user.id !== user?.id ? (
                      <select
                        className="input w-36"
                        value={m.role}
                        onChange={(e) => updateMemberRole.mutate({ userId: m.user.id, role: e.target.value })}
                      >
                        <option value="reader">Lecteur</option>
                        <option value="commentator">Commentateur</option>
                        <option value="editor">Editeur</option>
                      </select>
                    ) : (
                      <span className="badge">{m.role}</span>
                    )}
                    {(isCreator && m.user.id !== user?.id) && (
                      <button
                        type="button"
                        className="btn-outline text-red-600"
                        onClick={() => removeMember.mutate(m.user.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          {isCreator && (
            <form onSubmit={(e) => { e.preventDefault(); addMember.mutate(); }} className="card p-4 space-y-3">
              <h3 className="font-display font-semibold">Inviter un membre</h3>
              <div className="flex gap-2">
                <input className="input flex-1" type="email" placeholder="Email de l'utilisateur" value={newMember.email} onChange={(e) => setNewMember({ ...newMember, email: e.target.value })} required />
                <select className="input w-32" value={newMember.role} onChange={(e) => setNewMember({ ...newMember, role: e.target.value })}>
                  <option value="reader">Lecteur</option>
                  <option value="commentator">Commentateur</option>
                  <option value="editor">Editeur</option>
                </select>
                <button type="submit" className="btn-primary">
                  <UserPlus className="w-4 h-4" /> Inviter
                </button>
              </div>
            </form>
          )}
          {!isCreator && user?.id && (
            <button
              type="button"
              className="btn-outline text-red-600"
              onClick={() => removeMember.mutate(user.id)}
            >
              Quitter ce cookbook
            </button>
          )}
        </div>
      )}

      {tab === "discussion" && (
        <div className="card p-4 h-[60vh] flex flex-col">
          {!wsConnected && (
            <div className="mb-2 text-xs text-charcoal-500">
              Temps reel indisponible, synchronisation automatique active.
            </div>
          )}
          <div className="flex-1 overflow-y-auto space-y-2 mb-3">
            {allMessages.length === 0 ? (
              <div className="text-sm text-charcoal-500 text-center py-8">Aucun message. Lancez la conversation !</div>
            ) : (
              allMessages.map((m) => (
                <div key={m.id} className="flex gap-2">
                  <div className="w-8 h-8 rounded-full bg-tomato-100 text-tomato-700 text-xs flex items-center justify-center font-semibold flex-shrink-0">
                    {(m.author?.username || "?").slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <div className="text-xs text-charcoal-500">{m.author?.username || `User ${m.author_id}`}</div>
                    <div className="text-sm text-charcoal-900">{m.content}</div>
                  </div>
                </div>
              ))
            )}
          </div>
          {canDiscuss ? (
            <form
              onSubmit={(e) => { e.preventDefault(); if (msgContent.trim()) { sendMessage.mutate(msgContent); setMsgContent(""); } }}
              className="flex gap-2"
            >
              <input className="input" placeholder="Votre message..." value={msgContent} onChange={(e) => setMsgContent(e.target.value)} />
              <button type="submit" className="btn-primary"><Send className="w-4 h-4" /></button>
            </form>
          ) : (
            <div className="text-xs text-charcoal-500 text-center">Vous devez etre membre du cookbook pour participer.</div>
          )}
        </div>
      )}

      {tab === "settings" && isCreator && (
        <div className="space-y-4">
          <form
            onSubmit={(e) => { e.preventDefault(); updateCookbook.mutate(); }}
            className="card p-5 space-y-3"
          >
            <h3 className="font-display font-semibold text-charcoal-900">Parametres du cookbook</h3>
            <div>
              <label className="label">Nom</label>
              <input
                className="input"
                required
                value={settingsForm.name}
                onChange={(e) => setSettingsForm({ ...settingsForm, name: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Description</label>
              <textarea
                className="input"
                rows={2}
                value={settingsForm.description}
                onChange={(e) => setSettingsForm({ ...settingsForm, description: e.target.value })}
              />
            </div>
            <button type="submit" className="btn-primary" disabled={updateCookbook.isPending}>
              {updateCookbook.isPending ? "Enregistrement..." : "Enregistrer"}
            </button>
          </form>

          <div className="card p-5 space-y-3 border-red-200">
            <h3 className="font-display font-semibold text-red-700">Zone de danger</h3>
            <p className="text-sm text-charcoal-600">La suppression d un cookbook est definitive.</p>
            <button
              type="button"
              className="btn-outline text-red-600"
              onClick={() => {
                if (window.confirm("Supprimer ce cookbook definitivement ?")) {
                  deleteCookbook.mutate();
                }
              }}
            >
              <Trash2 className="w-4 h-4" /> Supprimer le cookbook
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
