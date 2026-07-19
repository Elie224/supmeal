import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ListChecks, Plus, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import type { ShoppingListDetail, ShoppingListSummary } from "../lib/types";

export default function ShoppingPage() {
  const qc = useQueryClient();
  const [selectedListId, setSelectedListId] = useState<number | null>(null);
  const [newItem, setNewItem] = useState({ name: "", quantity: "", unit: "" });

  const listsQ = useQuery({
    queryKey: ["shopping", "lists"],
    queryFn: async () => (await api.get<ShoppingListSummary[]>("/shopping")).data,
  });

  const effectiveListId = useMemo(() => {
    if (selectedListId) return selectedListId;
    return listsQ.data?.[0]?.id ?? null;
  }, [selectedListId, listsQ.data]);

  const detailQ = useQuery({
    queryKey: ["shopping", "detail", effectiveListId],
    enabled: !!effectiveListId,
    queryFn: async () => (await api.get<ShoppingListDetail>(`/shopping/${effectiveListId}`)).data,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["shopping", "lists"] });
    qc.invalidateQueries({ queryKey: ["shopping", "detail", effectiveListId] });
  };

  const toggleItem = useMutation({
    mutationFn: async (vars: { id: number; nextChecked: boolean }) =>
      await api.patch(`/shopping/${effectiveListId}/items/${vars.id}`, { is_checked: vars.nextChecked }),
    onSuccess: invalidate,
  });

  const deleteItem = useMutation({
    mutationFn: async (id: number) => await api.delete(`/shopping/${effectiveListId}/items/${id}`),
    onSuccess: invalidate,
  });

  const addItem = useMutation({
    mutationFn: async () =>
      await api.post(`/shopping/${effectiveListId}/items`, {
        name: newItem.name,
        quantity: newItem.quantity ? Number(newItem.quantity) : null,
        unit: newItem.unit || null,
      }),
    onSuccess: () => {
      setNewItem({ name: "", quantity: "", unit: "" });
      invalidate();
    },
  });

  const completeList = useMutation({
    mutationFn: async (completed: boolean) =>
      await api.patch(`/shopping/${effectiveListId}`, { is_completed: completed }),
    onSuccess: () => {
      invalidate();
      qc.invalidateQueries({ queryKey: ["shopping", "detail", effectiveListId] });
    },
  });

  const deleteList = useMutation({
    mutationFn: async () => await api.delete(`/shopping/${effectiveListId}`),
    onSuccess: () => {
      setSelectedListId(null);
      qc.invalidateQueries({ queryKey: ["shopping", "lists"] });
      qc.invalidateQueries({ queryKey: ["shopping", "detail"] });
    },
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display font-bold text-2xl text-charcoal-900">Listes de courses</h1>
        <div className="text-sm text-charcoal-500">Gerees automatiquement depuis le planning</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
        <aside className="card p-3 space-y-2 max-h-[70vh] overflow-y-auto">
          <h2 className="font-display font-semibold text-charcoal-900">Mes listes</h2>
          {listsQ.isLoading && <div className="text-sm text-charcoal-500">Chargement...</div>}
          {!listsQ.isLoading && (listsQ.data?.length || 0) === 0 && (
            <div className="text-sm text-charcoal-500">Aucune liste. Genere une liste depuis le planning.</div>
          )}
          {listsQ.data?.map((l) => (
            <button
              key={l.id}
              onClick={() => setSelectedListId(l.id)}
              className={`w-full text-left rounded p-2 border transition ${
                effectiveListId === l.id
                  ? "border-tomato-300 bg-tomato-50"
                  : "border-cream-200 hover:bg-cream-50"
              }`}
            >
              <div className="flex items-center gap-2">
                <ListChecks className="w-4 h-4 text-charcoal-600" />
                <span className="font-medium text-charcoal-900 truncate">{l.name}</span>
              </div>
              <div className="text-xs text-charcoal-500 mt-1">
                {l.start_date || "?"} - {l.end_date || "?"}
              </div>
              <div className="text-xs mt-1">
                {l.is_completed ? "Terminee" : "En cours"}
              </div>
            </button>
          ))}
        </aside>

        <section className="card p-4 space-y-4 min-h-[320px]">
          {!effectiveListId && <div className="text-sm text-charcoal-500">Selectionne une liste.</div>}

          {effectiveListId && detailQ.isLoading && <div className="text-sm text-charcoal-500">Chargement...</div>}

          {effectiveListId && detailQ.data && (
            <>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="font-display font-semibold text-lg text-charcoal-900">{detailQ.data.name}</h2>
                  <p className="text-xs text-charcoal-500">
                    {detailQ.data.start_date || "?"} - {detailQ.data.end_date || "?"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => completeList.mutate(!detailQ.data.is_completed)}
                    className="btn-outline text-xs"
                  >
                    {detailQ.data.is_completed ? "Marquer en cours" : "Marquer terminee"}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteList.mutate()}
                    className="btn-outline text-xs text-red-600"
                  >
                    <Trash2 className="w-4 h-4" /> Supprimer
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-[1fr_120px_120px_auto] gap-2">
                <input
                  className="input text-sm"
                  placeholder="Ajouter un ingredient"
                  value={newItem.name}
                  onChange={(e) => setNewItem((s) => ({ ...s, name: e.target.value }))}
                />
                <input
                  className="input text-sm"
                  type="number"
                  step="0.1"
                  placeholder="Qt"
                  value={newItem.quantity}
                  onChange={(e) => setNewItem((s) => ({ ...s, quantity: e.target.value }))}
                />
                <input
                  className="input text-sm"
                  placeholder="Unite"
                  value={newItem.unit}
                  onChange={(e) => setNewItem((s) => ({ ...s, unit: e.target.value }))}
                />
                <button
                  type="button"
                  className="btn-primary"
                  disabled={!newItem.name.trim()}
                  onClick={() => addItem.mutate()}
                >
                  <Plus className="w-4 h-4" /> Ajouter
                </button>
              </div>

              <div className="space-y-2">
                {detailQ.data.items.length === 0 && (
                  <div className="text-sm text-charcoal-500">Aucun item dans cette liste.</div>
                )}
                {detailQ.data.items.map((it) => (
                  <div key={it.id} className="flex items-center justify-between rounded border border-cream-200 p-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={it.is_checked}
                        onChange={(e) => toggleItem.mutate({ id: it.id, nextChecked: e.target.checked })}
                      />
                      <span className={`text-sm ${it.is_checked ? "line-through text-charcoal-400" : "text-charcoal-800"}`}>
                        {it.name}
                        {it.quantity != null ? ` - ${it.quantity}` : ""}
                        {it.unit ? ` ${it.unit}` : ""}
                      </span>
                    </label>
                    <button
                      type="button"
                      className="text-xs text-red-600 hover:underline"
                      onClick={() => deleteItem.mutate(it.id)}
                    >
                      Supprimer
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
