import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import type { Recipe, Ingredient, Step } from "../lib/types";

export default function RecipeEditPage() {
  const { id } = useParams<{ id: string }>();
  const isNew = !id || id === "new";
  const navigate = useNavigate();

  const [form, setForm] = useState({
    title: "",
    description: "",
    source_url: "",
    servings: 4,
    prep_time_minutes: 0,
    cook_time_minutes: 0,
    difficulty: "",
    cuisine_type: "",
    image_url: "",
    is_favorite: false,
    is_public: false,
    tag_ids: [] as number[],
  });
  const [ingredients, setIngredients] = useState<Ingredient[]>([{ name: "", position: 0 }]);
  const [steps, setSteps] = useState<Step[]>([{ content: "", position: 0 }]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isNew) {
      api.get<Recipe>(`/recipes/${id}`).then((r) => {
        const data = r.data;
        setForm({
          title: data.title,
          description: data.description || "",
          source_url: data.source_url || "",
          servings: data.servings,
          prep_time_minutes: data.prep_time_minutes,
          cook_time_minutes: data.cook_time_minutes,
          difficulty: data.difficulty || "",
          cuisine_type: data.cuisine_type || "",
          image_url: data.image_url || "",
          is_favorite: data.is_favorite,
          is_public: data.is_public,
          tag_ids: data.tags.map((t) => t.id),
        });
        setIngredients(data.ingredients.length > 0 ? data.ingredients : [{ name: "", position: 0 }]);
        setSteps(data.steps.length > 0 ? data.steps : [{ content: "", position: 0 }]);
      });
    }
  }, [id, isNew]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const payload = {
      ...form,
      ingredients: ingredients.filter((i) => i.name.trim()).map((i, idx) => ({ ...i, position: idx })),
      steps: steps.filter((s) => s.content.trim()).map((s, idx) => ({ ...s, position: idx })),
    };
    try {
      if (isNew) {
        const { data } = await api.post("/recipes", payload);
        navigate(`/recipes/${data.id}`);
      } else {
        await api.patch(`/recipes/${id}`, payload);
        navigate(`/recipes/${id}`);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Erreur");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="font-display font-bold text-2xl text-charcoal-900 mb-6">
        {isNew ? "Nouvelle recette" : "Modifier la recette"}
      </h1>
      <form onSubmit={onSubmit} className="card p-6 space-y-5">
        {error && <div className="rounded bg-red-50 border border-red-200 text-red-700 text-sm p-3">{error}</div>}
        <div>
          <label className="label">Titre *</label>
          <input className="input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea className="input" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label">Portions</label>
            <input type="number" min={1} className="input" value={form.servings} onChange={(e) => setForm({ ...form, servings: +e.target.value })} />
          </div>
          <div>
            <label className="label">Prep (min)</label>
            <input type="number" min={0} className="input" value={form.prep_time_minutes} onChange={(e) => setForm({ ...form, prep_time_minutes: +e.target.value })} />
          </div>
          <div>
            <label className="label">Cuisson (min)</label>
            <input type="number" min={0} className="input" value={form.cook_time_minutes} onChange={(e) => setForm({ ...form, cook_time_minutes: +e.target.value })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Difficulte</label>
            <input className="input" placeholder="facile, moyen, difficile" value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value })} />
          </div>
          <div>
            <label className="label">Type de cuisine</label>
            <input className="input" placeholder="francaise, italienne..." value={form.cuisine_type} onChange={(e) => setForm({ ...form, cuisine_type: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label">URL de la source</label>
          <input className="input" type="url" value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="label !mb-0">Ingredients</label>
            <button type="button" onClick={() => setIngredients([...ingredients, { name: "", position: ingredients.length }])} className="btn-ghost text-xs">
              <Plus className="w-3 h-3" /> Ajouter
            </button>
          </div>
          <div className="space-y-2">
            {ingredients.map((ing, idx) => (
              <div key={idx} className="flex gap-2">
                <input className="input flex-1" placeholder="Nom" value={ing.name} onChange={(e) => setIngredients(ingredients.map((i, ix) => ix === idx ? { ...i, name: e.target.value } : i))} />
                <input className="input w-24" type="number" step="0.1" placeholder="Qte" value={ing.quantity ?? ""} onChange={(e) => setIngredients(ingredients.map((i, ix) => ix === idx ? { ...i, quantity: e.target.value ? +e.target.value : null } : i))} />
                <input className="input w-24" placeholder="Unite" value={ing.unit ?? ""} onChange={(e) => setIngredients(ingredients.map((i, ix) => ix === idx ? { ...i, unit: e.target.value } : i))} />
                <button type="button" onClick={() => setIngredients(ingredients.filter((_, ix) => ix !== idx))} className="btn-ghost text-red-500">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="label !mb-0">Etapes</label>
            <button type="button" onClick={() => setSteps([...steps, { content: "", position: steps.length }])} className="btn-ghost text-xs">
              <Plus className="w-3 h-3" /> Ajouter
            </button>
          </div>
          <div className="space-y-2">
            {steps.map((s, idx) => (
              <div key={idx} className="flex gap-2">
                <span className="flex-shrink-0 w-6 h-9 flex items-center justify-center text-charcoal-500 text-sm">{idx + 1}.</span>
                <textarea className="input flex-1" rows={2} value={s.content} onChange={(e) => setSteps(steps.map((st, ix) => ix === idx ? { ...st, content: e.target.value } : st))} />
                <button type="button" onClick={() => setSteps(steps.filter((_, ix) => ix !== idx))} className="btn-ghost text-red-500">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-3 pt-3">
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Enregistrement..." : isNew ? "Creer la recette" : "Enregistrer"}
          </button>
          <button type="button" onClick={() => navigate(-1)} className="btn-outline">Annuler</button>
        </div>
      </form>
    </div>
  );
}
