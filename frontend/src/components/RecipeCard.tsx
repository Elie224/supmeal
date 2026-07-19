import { Link } from "react-router-dom";
import { Heart, Clock, Users } from "lucide-react";
import { formatDuration, cn } from "../lib/utils";
import type { RecipeSummary } from "../lib/types";

interface Props {
  recipe: RecipeSummary;
  onToggleFavorite?: (id: number) => void;
}

export default function RecipeCard({ recipe, onToggleFavorite }: Props) {
  return (
    <Link
      to={`/recipes/${recipe.id}`}
      className="card overflow-hidden group hover:shadow-card transition-shadow"
    >
      <div className="aspect-[16/10] bg-cream-100 relative">
        {recipe.image_url ? (
          <img src={recipe.image_url} alt={recipe.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-charcoal-300 text-4xl">&#127869;</div>
        )}
        {onToggleFavorite && (
          <button
            onClick={(e) => {
              e.preventDefault();
              onToggleFavorite(recipe.id);
            }}
            className="absolute top-2 right-2 p-1.5 rounded-full bg-white/80 hover:bg-white"
          >
            <Heart
              className={cn("w-4 h-4", recipe.is_favorite ? "fill-tomato-500 text-tomato-500" : "text-charcoal-500")}
            />
          </button>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-display font-semibold text-base text-charcoal-900 line-clamp-1">{recipe.title}</h3>
        {recipe.description && (
          <p className="text-xs text-charcoal-500 mt-0.5 line-clamp-2">{recipe.description}</p>
        )}
        <div className="mt-2 flex items-center gap-3 text-xs text-charcoal-500">
          <span className="inline-flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDuration(recipe.prep_time_minutes + recipe.cook_time_minutes)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Users className="w-3 h-3" />
            {recipe.servings} pers.
          </span>
        </div>
        {recipe.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {recipe.tags.slice(0, 3).map((t) => (
              <span key={t.id} className="badge">{t.name}</span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}