import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles, X, Plus, Clock, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { RecipeSuggestion as RecipeSuggestionType, RecipeSuggestPayload } from "../lib/types";
import { formatDuration, cn } from "../lib/utils";

export default function SuggestionsPage() {
  const [ingredients, setIngredients] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [maxPrepTime, setMaxPrepTime] = useState<number | "">("");
  const [maxCookTime, setMaxCookTime] = useState<number | "">("");

  const suggest = useMutation({
    mutationFn: async (payload: RecipeSuggestPayload) =>
      (await api.post<RecipeSuggestionType[]>("/recipes/suggest", payload)).data,
  });

  const addIngredient = (raw: string) => {
    const v = raw.trim();
    if (!v) return;
    if (ingredients.includes(v)) return;
    if (ingredients.length >= 50) return;
    setIngredients([...ingredients, v]);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (draft) addIngredient(draft);
    setDraft("");
    if (ingredients.length === 0 && !draft) return;
    const payload: RecipeSuggestPayload = {
      ingredients: [...ingredients, ...(draft ? [draft.trim()] : [])].filter((x) => x),
    };
    if (maxPrepTime !== "") payload.max_prep_time = maxPrepTime as number;
    if (maxCookTime !== "") payload.max_cook_time = maxCookTime as number;
    suggest.mutate(payload);
  };

  const onRemove = (name: string) => {
    setIngredients(ingredients.filter((x) => x !== name));
  };

  const suggestions = suggest.data ?? [];
  const empty = suggest.isSuccess && ingredients.length === 0;

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-2xl font-bold text-charcoal-900 inline-flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-tomato-500" />
            Suggestions de recettes
          </h1>
          <p className="text-sm text-charcoal-500 mt-1">
            Saisissez les ingredients que vous avez sous la main et trouvez une recette realisable.
          </p>
        </div>
      </header>

      <form onSubmit={onSubmit} className="card p-4 space-y-3">
        <div>
          <label htmlFor="ingredient" className="block text-sm font-medium text-charcoal-700 mb-1">
            Ingredients disponibles
          </label>
          <div className="flex gap-2">
            <input
              id="ingredient"
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  if (draft) {
                    addIngredient(draft);
                    setDraft("");
                  }
                }
              }}
              placeholder="Ex : tomate, oignon, ail..."
              className="input flex-1"
              maxLength={120}
            />
            <button
              type="button"
              onClick={() => {
                addIngredient(draft);
                setDraft("");
              }}
              className="btn-secondary inline-flex items-center gap-1"
              disabled={!draft.trim()}
            >
              <Plus className="w-4 h-4" />
              Ajouter
            </button>
          </div>
          {ingredients.length > 0 && (
            <ul className="flex flex-wrap gap-1.5 mt-3">
              {ingredients.map((ing) => (
                <li
                  key={ing}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-tomato-100 text-tomato-700 text-xs"
                >
                  {ing}
                  <button
                    type="button"
                    onClick={() => onRemove(ing)}
                    className="hover:text-tomato-900"
                    aria-label={`Retirer ${ing}`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label htmlFor="max_prep" className="block text-xs font-medium text-charcoal-700 mb-1">
              Temps de preparation max (min)
            </label>
            <input
              id="max_prep"
              type="number"
              min={0}
              max={1440}
              value={maxPrepTime}
              onChange={(e) => setMaxPrepTime(e.target.value === "" ? "" : Number(e.target.value))}
              className="input"
            />
          </div>
          <div>
            <label htmlFor="max_cook" className="block text-xs font-medium text-charcoal-700 mb-1">
              Temps de cuisson max (min)
            </label>
            <input
              id="max_cook"
              type="number"
              min={0}
              max={1440}
              value={maxCookTime}
              onChange={(e) => setMaxCookTime(e.target.value === "" ? "" : Number(e.target.value))}
              className="input"
            />
          </div>
        </div>

        <div className="flex items-center justify-between gap-2">
          <p className="text-xs text-charcoal-500">
            {ingredients.length} ingredient{ingredients.length > 1 ? "s" : ""} ajoute
            {ingredients.length > 1 ? "s" : ""}.
          </p>
          <button
            type="submit"
            className="btn-primary"
            disabled={suggest.isPending || (ingredients.length === 0 && !draft.trim())}
          >
            {suggest.isPending ? "Recherche..." : "Trouver des recettes"}
          </button>
        </div>
      </form>

      {suggest.isError && (
        <div className="card p-4 border border-danger text-danger">
          Une erreur est survenue. Verifiez votre connexion et reessayez.
        </div>
      )}

      {empty && (
        <div className="card p-8 text-center text-charcoal-500">
          Aucun ingredient. Ajoutez-en au moins un pour obtenir des suggestions.
        </div>
      )}

      {suggestions.length === 0 && suggest.isSuccess && ingredients.length > 0 && (
        <div className="card p-8 text-center text-charcoal-500">
          Aucune recette ne matche vos ingredients. Essayez d&apos;enlever un filtre ou
          d&apos;ajouter plus d&apos;ingredients.
        </div>
      )}

      {suggestions.length > 0 && (
        <ul className="space-y-3">
          {suggestions.map((s) => (
            <li key={s.recipe.id} className="card p-4 flex gap-4 items-start">
              <Link
                to={`/recipes/${s.recipe.id}`}
                className="shrink-0 w-20 h-20 rounded bg-cream-100 overflow-hidden flex items-center justify-center text-3xl"
              >
                {s.recipe.image_url ? (
                  <img
                    src={s.recipe.image_url}
                    alt={s.recipe.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span>&#127869;</span>
                )}
              </Link>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <Link
                    to={`/recipes/${s.recipe.id}`}
                    className="font-display font-semibold text-charcoal-900 hover:text-tomato-600"
                  >
                    {s.recipe.title}
                  </Link>
                  <span
                    className={cn(
                      "text-xs font-semibold px-2 py-1 rounded-full whitespace-nowrap",
                      s.match_score >= 0.8
                        ? "bg-success/10 text-success"
                        : s.match_score >= 0.5
                          ? "bg-warning/10 text-warning"
                          : "bg-cream-100 text-charcoal-700"
                    )}
                  >
                    {Math.round(s.match_score * 100)}% de matching
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-3 text-xs text-charcoal-500">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDuration(s.recipe.prep_time_minutes + s.recipe.cook_time_minutes)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {s.recipe.servings} pers.
                  </span>
                </div>
                <div className="mt-2 grid sm:grid-cols-2 gap-2 text-xs">
                  <div>
                    <p className="font-medium text-success mb-0.5">
                      Vous avez ({s.matched_ingredients.length})
                    </p>
                    <p className="text-charcoal-700">{s.matched_ingredients.join(", ")}</p>
                  </div>
                  {s.missing_ingredients.length > 0 && (
                    <div>
                      <p className="font-medium text-warning mb-0.5">
                        Il manque ({s.missing_ingredients.length})
                      </p>
                      <p className="text-charcoal-700">{s.missing_ingredients.join(", ")}</p>
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
