import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Heart, Calendar, ArrowLeft, Trash2, Pencil } from "lucide-react";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import { formatDuration, cn } from "../lib/utils";
import type { Recipe } from "../lib/types";

export default function RecipePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [comment, setComment] = useState("");

  const recipeQ = useQuery({
    queryKey: ["recipe", id],
    queryFn: async () => (await api.get<Recipe>(`/recipes/${id}`)).data,
    enabled: !!id,
  });

  const commentsQ = useQuery({
    queryKey: ["comments", id],
    queryFn: async () => (await api.get(`/recipes/${id}/comments`)).data,
    enabled: !!id,
  });

  const fav = useMutation({
    mutationFn: async () => (await api.post(`/recipes/${id}/favorite`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recipe", id] }),
  });

  const del = useMutation({
    mutationFn: async () => (await api.delete(`/recipes/${id}`)).data,
    onSuccess: () => navigate("/"),
  });

  const addComment = useMutation({
    mutationFn: async (content: string) => (await api.post(`/recipes/${id}/comments`, { content })).data,
    onSuccess: () => {
      setComment("");
      qc.invalidateQueries({ queryKey: ["comments", id] });
    },
  });

  if (recipeQ.isLoading) return <div>Chargement...</div>;
  if (!recipeQ.data) return <div>Recette introuvable</div>;

  const r = recipeQ.data;
  const isOwner = user?.id === r.owner_id;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/" className="btn-ghost text-sm">
          <ArrowLeft className="w-4 h-4" /> Retour
        </Link>
        <div className="flex gap-2">
          <button onClick={() => fav.mutate()} className={cn("btn-outline", r.is_favorite && "text-tomato-600 border-tomato-500")}>
            <Heart className={cn("w-4 h-4", r.is_favorite && "fill-tomato-500")} />
            {r.is_favorite ? "Favori" : "Ajouter aux favoris"}
          </button>
          <button className="btn-outline">
            <Calendar className="w-4 h-4" /> Planifier
          </button>
          {isOwner && (
            <>
              <Link to={`/recipes/${r.id}/edit`} className="btn-outline">
                <Pencil className="w-4 h-4" /> Editer
              </Link>
              <button onClick={() => del.mutate()} className="btn-outline text-red-600">
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      <div className="card overflow-hidden">
        {r.image_url && <img src={r.image_url} alt={r.title} className="w-full h-64 object-cover" />}
        <div className="p-6">
          <h1 className="font-display font-bold text-3xl text-charcoal-900">{r.title}</h1>
          {r.description && <p className="text-charcoal-700 mt-2">{r.description}</p>}
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-charcoal-500">
            <span>&#9201; Preparation : {formatDuration(r.prep_time_minutes)}</span>
            <span>&#128293; Cuisson : {formatDuration(r.cook_time_minutes)}</span>
            <span>&#127869; {r.servings} portions</span>
            {r.difficulty && <span> Niveau : {r.difficulty}</span>}
            {r.cuisine_type && <span> {r.cuisine_type}</span>}
          </div>
          {r.tags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {r.tags.map((t) => <span key={t.id} className="badge">{t.name}</span>)}
            </div>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card p-5">
          <h2 className="font-display font-semibold text-lg text-charcoal-900 mb-3">Ingredients</h2>
          <ul className="space-y-1.5">
            {r.ingredients.map((ing) => (
              <li key={ing.id} className="flex items-baseline gap-2 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-tomato-500 mt-1.5" />
                <span className="text-charcoal-900">{ing.name}</span>
                {ing.quantity != null && (
                  <span className="text-charcoal-500">{ing.quantity}{ing.unit ? ` ${ing.unit}` : ""}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
        <div className="card p-5">
          <h2 className="font-display font-semibold text-lg text-charcoal-900 mb-3">Etapes</h2>
          <ol className="space-y-3">
            {r.steps.map((s, i) => (
              <li key={s.id} className="flex gap-3 text-sm">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-tomato-500 text-cream-50 text-xs flex items-center justify-center font-semibold">
                  {i + 1}
                </span>
                <span className="text-charcoal-700 whitespace-pre-line">{s.content}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {r.cookbook_id && (
        <div className="card p-5">
          <h2 className="font-display font-semibold text-lg text-charcoal-900 mb-3">Commentaires</h2>
          <div className="space-y-3 mb-4">
            {commentsQ.data && commentsQ.data.length > 0 ? (
              commentsQ.data.map((c: any) => (
                <div key={c.id} className="border-l-2 border-cream-200 pl-3 py-1">
                  <div className="text-xs text-charcoal-500">Utilisateur #{c.author_id}</div>
                  <div className="text-sm text-charcoal-700">{c.content}</div>
                </div>
              ))
            ) : (
              <div className="text-sm text-charcoal-500">Aucun commentaire pour le moment.</div>
            )}
          </div>
          <form
            onSubmit={(e) => { e.preventDefault(); if (comment.trim()) addComment.mutate(comment); }}
            className="flex gap-2"
          >
            <input
              className="input"
              placeholder="Votre commentaire..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <button type="submit" className="btn-primary" disabled={!comment.trim()}>Envoyer</button>
          </form>
        </div>
      )}
    </div>
  );
}