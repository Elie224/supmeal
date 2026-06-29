import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Send, UserPlus } from "lucide-react";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import RecipeCard from "../components/RecipeCard";
import type { Cookbook, Message, Recipe } from "../lib/types";

type Tab = "recipes" | "members" | "discussion" | "settings";

export default function CookbookPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [tab, setTab] = useState<Tab>("recipes");
  const [search, setSearch] = useState("");
  const [msgContent, setMsgContent] = useState("");
  const [newMember, setNewMember] = useState({ email: "", role: "reader" });
  const wsRef = useRef<WebSocket | null>(null);
  const [liveMessages, setLiveMessages] = useState<Message[]>([]);

  const cookbookQ = useQuery({
    queryKey: ["cookbook", id],
    queryFn: async () => (await api.get<Cookbook>(`/cookbooks/${id}`)).data,
    enabled: !!id,
  });

  const recipesQ = useQuery({
    queryKey: ["cookbook-recipes", id, search],
    queryFn: async () => (await api.get<Recipe[]>(`/cookbooks/${id}/recipes`, { params: { search: search || undefined } })).data,
    enabled: !!id && tab === "recipes",
  });

  const messagesQ = useQuery({
    queryKey: ["cookbook-messages", id],
    queryFn: async () => (await api.get<Message[]>(`/cookbooks/${id}/messages`)).data,
    enabled: !!id && tab === "discussion",
  });

  useEffect(() => {
    if (tab === "discussion" && id) {
      const token = localStorage.getItem("supmeal_token");
      const wsBase = (import.meta.env.VITE_API_URL || "/api/v1").replace(/^http/, "ws");
      const ws = new WebSocket(`${wsBase}/cookbooks/ws/${id}?token=${token}`);
      ws.onmessage = (ev) => {
        const msg: Message = JSON.parse(ev.data);
        setLiveMessages((prev) => [...prev, msg]);
      };
      wsRef.current = ws;
      return () => { ws.close(); };
    }
  }, [tab, id]);

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

  if (cookbookQ.isLoading) return <div>Chargement...</div>;
  if (!cookbookQ.data) return <div>Cookbook introuvable</div>;

  const cb = cookbookQ.data;
  const myMember = cb.members.find((m) => m.user.id === user?.id);
  const myRole = myMember?.role;
  const canDiscuss = myRole && myRole !== "reader";
  const isCreator = myRole === "creator";

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
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-500" />
            <input className="input pl-9" placeholder="Rechercher dans le cookbook..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          {recipesQ.data && recipesQ.data.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {recipesQ.data.map((r) => <RecipeCard key={r.id} recipe={r as any} />)}
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
                  <span className="badge">{m.role}</span>
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
        </div>
      )}

      {tab === "discussion" && (
        <div className="card p-4 h-[60vh] flex flex-col">
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
            <div className="text-xs text-charcoal-500 text-center">Les lecteurs ne peuvent pas envoyer de messages.</div>
          )}
        </div>
      )}

      {tab === "settings" && isCreator && (
        <div className="card p-5 text-sm text-charcoal-500">
          <p>Les parametres avances du cookbook (renommer, supprimer) sont disponibles pour le createur.</p>
        </div>
      )}
    </div>
  );
}
