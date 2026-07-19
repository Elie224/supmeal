import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Filter } from "lucide-react";
import { api } from "../lib/api";
import RecipeCard from "../components/RecipeCard";
import type { RecipeSummary, CookbookSummary } from "../lib/types";
import { cn } from "../lib/utils";

export default function DashboardPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [favOnly, setFavOnly] = useState(false);
  const [tagFilter, setTagFilter] = useState<number | null>(null);
  const [tagCategoryFilter, setTagCategoryFilter] = useState<string>("");
  const [cookbookFilter, setCookbookFilter] = useState<number | null>(null);
  const [ingredientFilter, setIngredientFilter] = useState("");
  const [maxPrepTime, setMaxPrepTime] = useState<number | "">("");
  const [maxCookTime, setMaxCookTime] = useState<number | "">("");

  const recipesQ = useQuery({
    queryKey: [
      "recipes",
      search,
      favOnly,
      tagFilter,
      tagCategoryFilter,
      cookbookFilter,
      ingredientFilter,
      maxPrepTime,
      maxCookTime,
    ],
    queryFn: async () => {
      const params: Record<string, any> = {};
      if (search) params.search = search;
      if (favOnly) params.favorites_only = true;
      if (tagFilter) params.tag_ids = [tagFilter];
      if (tagCategoryFilter) params.tag_category = tagCategoryFilter;
      if (cookbookFilter) params.cookbook_id = cookbookFilter;
      if (ingredientFilter) params.ingredient = ingredientFilter;
      if (maxPrepTime !== "") params.max_prep_time = maxPrepTime;
      if (maxCookTime !== "") params.max_cook_time = maxCookTime;
      const { data } = await api.get<RecipeSummary[]>("/recipes", { params });
      return data;
    },
  });

  const cookbooksQ = useQuery({
    queryKey: ["cookbooks"],
    queryFn: async () => (await api.get<CookbookSummary[]>("/cookbooks")).data,
  });

  const tagsQ = useQuery({
    queryKey: ["tags"],
    queryFn: async () => (await api.get("/tags")).data,
  });

  const fav = useMutation({
    mutationFn: async (id: number) => (await api.post(`/recipes/${id}/favorite`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recipes"] }),
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <section className="card p-4">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-500" />
            <input
              className="input pl-9"
              placeholder="Rechercher une recette (titre, ingredient, tag...)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button
            onClick={() => setFavOnly((v) => !v)}
            className={cn("btn-outline", favOnly && "bg-tomato-100 border-tomato-500 text-tomato-700")}
          >
            <Filter className="w-4 h-4" />
            Favoris
          </button>
        </div>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2">
          <select
            className="input"
            value={cookbookFilter ?? ""}
            onChange={(e) => setCookbookFilter(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Tous les cookbooks</option>
            {cookbooksQ.data?.map((cb) => (
              <option key={cb.id} value={cb.id}>{cb.name}</option>
            ))}
          </select>
          <input
            className="input"
            placeholder="Ingredient"
            value={ingredientFilter}
            onChange={(e) => setIngredientFilter(e.target.value)}
          />
          <input
            className="input"
            type="number"
            min={0}
            placeholder="Prep max (min)"
            value={maxPrepTime}
            onChange={(e) => setMaxPrepTime(e.target.value ? Number(e.target.value) : "")}
          />
          <input
            className="input"
            type="number"
            min={0}
            placeholder="Cuisson max (min)"
            value={maxCookTime}
            onChange={(e) => setMaxCookTime(e.target.value ? Number(e.target.value) : "")}
          />
          <select
            className="input"
            value={tagCategoryFilter}
            onChange={(e) => setTagCategoryFilter(e.target.value)}
          >
            <option value="">Toutes categories</option>
            {Array.from(new Set((tagsQ.data || []).map((t: any) => t.category).filter(Boolean))).map((category: any) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>
        {tagsQ.data && tagsQ.data.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={() => setTagFilter(null)}
              className={cn("badge cursor-pointer", !tagFilter && "bg-tomato-500 text-cream-50")}
            >
              Tous
            </button>
            {tagsQ.data.map((t: any) => (
              <button
                key={t.id}
                onClick={() => setTagFilter(t.id === tagFilter ? null : t.id)}
                className={cn("badge cursor-pointer", tagFilter === t.id && "bg-tomato-500 text-cream-50")}
              >
                {t.name}
              </button>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="font-display font-semibold text-xl text-charcoal-900 mb-3">Mes recettes</h2>
        {recipesQ.isLoading ? (
          <div className="text-charcoal-500">Chargement...</div>
        ) : recipesQ.data && recipesQ.data.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {recipesQ.data.map((r) => (
              <RecipeCard key={r.id} recipe={r} onToggleFavorite={(id) => fav.mutate(id)} />
            ))}
          </div>
        ) : (
          <div className="card p-8 text-center text-charcoal-500">
            Aucune recette. Cliquez sur "Nouvelle recette" pour commencer.
          </div>
        )}
      </section>

      <section>
        <h2 className="font-display font-semibold text-xl text-charcoal-900 mb-3">Cookbooks partages</h2>
        {cookbooksQ.data && cookbooksQ.data.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {cookbooksQ.data.map((cb) => (
              <a key={cb.id} href={`/cookbooks/${cb.id}`} className="card p-4 hover:shadow-card">
                <div className="font-display font-semibold text-base text-charcoal-900">{cb.name}</div>
                {cb.description && <p className="text-sm text-charcoal-500 mt-1 line-clamp-2">{cb.description}</p>}
                <div className="mt-3 flex items-center gap-3 text-xs text-charcoal-500">
                  <span>{cb.member_count} membres</span>
                  <span>{cb.recipe_count} recettes</span>
                  {cb.my_role && <span className="badge">{cb.my_role}</span>}
                </div>
              </a>
            ))}
          </div>
        ) : (
          <div className="card p-6 text-center text-charcoal-500 text-sm">
            Aucun cookbook. Creez-en un depuis la section "Mes cookbooks".
          </div>
        )}
      </section>
    </div>
  );
}