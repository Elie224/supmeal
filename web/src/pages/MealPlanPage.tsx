import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { addDays, format, startOfWeek } from "date-fns";
import { fr } from "date-fns/locale";
import { ChevronLeft, ChevronRight, ShoppingCart } from "lucide-react";
import { api } from "../lib/api";
import type { MealPlan, RecipeSummary } from "../lib/types";
import { useAuthStore } from "../stores/auth";

const SLOTS = ["breakfast", "lunch", "dinner", "snack"] as const;
const SLOT_LABELS: Record<string, string> = { breakfast: "Matin", lunch: "Midi", dinner: "Soir", snack: "Collation" };

export default function MealPlanPage() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const startStr = format(days[0], "yyyy-MM-dd");
  const endStr = format(days[6], "yyyy-MM-dd");

  const plansQ = useQuery({
    queryKey: ["plans", startStr, endStr],
    queryFn: async () => (await api.get<MealPlan[]>("/meal-plans", { params: { start_date: startStr, end_date: endStr } })).data,
  });

  const recipesQ = useQuery({
    queryKey: ["recipes", "all"],
    queryFn: async () => (await api.get<RecipeSummary[]>("/recipes", { params: { limit: 100 } })).data,
  });

  const add = useMutation({
    mutationFn: async (p: { recipe_id: number; planned_date: string; meal_slot: string }) =>
      (await api.post("/meal-plans", p)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plans", startStr, endStr] }),
  });

  const remove = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/meal-plans/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["plans", startStr, endStr] }),
  });

  const generateList = useMutation({
    mutationFn: async () => (await api.post("/shopping/generate", { start_date: startStr, end_date: endStr, name: `Semaine du ${startStr}` })).data,
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button onClick={() => setWeekStart(addDays(weekStart, -7))} className="btn-outline"><ChevronLeft className="w-4 h-4" /></button>
          <h1 className="font-display font-bold text-xl text-charcoal-900">
            Semaine du {format(weekStart, "d MMMM", { locale: fr })}
          </h1>
          <button onClick={() => setWeekStart(addDays(weekStart, 7))} className="btn-outline"><ChevronRight className="w-4 h-4" /></button>
        </div>
        <button
          onClick={() => generateList.mutate()}
          disabled={generateList.isPending}
          className="btn-primary"
        >
          <ShoppingCart className="w-4 h-4" /> Generer la liste de courses
        </button>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-cream-100">
              <th className="p-2 text-left text-xs font-semibold text-charcoal-700 w-24">Repas</th>
              {days.map((d) => (
                <th key={d.toString()} className="p-2 text-left text-xs font-semibold text-charcoal-700">
                  {format(d, "EEE d", { locale: fr })}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SLOTS.map((slot) => (
              <tr key={slot} className="border-t border-cream-200">
                <td className="p-2 text-xs font-medium text-charcoal-700">{SLOT_LABELS[slot]}</td>
                {days.map((d) => {
                  const dateStr = format(d, "yyyy-MM-dd");
                  const plan = plansQ.data?.find((p) => p.planned_date === dateStr && p.meal_slot === slot);
                  const recipe = recipesQ.data?.find((r) => r.id === plan?.recipe_id);
                  return (
                    <td key={dateStr} className="p-2 align-top">
                      {plan && recipe ? (
                        <div className="bg-tomato-100 rounded p-2 text-xs">
                          <div className="font-medium text-charcoal-900">{recipe.title}</div>
                          <button
                            onClick={() => remove.mutate(plan.id)}
                            className="text-tomato-700 hover:underline mt-1"
                          >
                            Retirer
                          </button>
                        </div>
                      ) : (
                        <select
                          className="input text-xs"
                          value=""
                          onChange={(e) => {
                            const v = e.target.value;
                            if (v) add.mutate({ recipe_id: +v, planned_date: dateStr, meal_slot: slot });
                          }}
                        >
                          <option value="">+ Ajouter</option>
                          {recipesQ.data?.map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}
                        </select>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}