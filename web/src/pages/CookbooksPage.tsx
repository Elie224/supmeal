import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api } from "../lib/api";
import type { CookbookSummary } from "../lib/types";
import { Link } from "react-router-dom";

export default function CookbooksPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const [page, setPage] = useState(0)
  const PAGE_SIZE = 12
  const list = useQuery({
    queryKey: ["cookbooks", page],
    queryFn: async () => (await api.get<CookbookSummary[]>("/cookbooks")).data,
  })
  const visibleCookbooks = list.data ? list.data.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE) : []
  const hasMore = list.data ? (page + 1) * PAGE_SIZE < list.data.length : false;

  const create = useMutation({
    mutationFn: async () => (await api.post("/cookbooks", { name, description })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cookbooks"] });
      setShowCreate(false);
      setName("");
      setDescription("");
    },
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display font-bold text-2xl text-charcoal-900">Mes cookbooks</h1>
        <button onClick={() => setShowCreate((v) => !v)} className="btn-primary">
          <Plus className="w-4 h-4" /> Creer un cookbook
        </button>
      </div>

      {showCreate && (
        <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="card p-5 space-y-3">
          <div>
            <label className="label">Nom</label>
            <input className="input" required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea className="input" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={create.isPending} className="btn-primary">Creer</button>
            <button type="button" onClick={() => setShowCreate(false)} className="btn-outline">Annuler</button>
          </div>
        </form>
      )}

      {list.data && list.data.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {visibleCookbooks.map((cb) => (
            <Link key={cb.id} to={`/cookbooks/${cb.id}`} className="card p-4 hover:shadow-card">
              <h3 className="font-display font-semibold text-lg text-charcoal-900">{cb.name}</h3>
              {cb.description && <p className="text-sm text-charcoal-500 mt-1 line-clamp-2">{cb.description}</p>}
              <div className="mt-3 flex items-center gap-3 text-xs text-charcoal-500">
                <span>{cb.member_count} membres</span>
                <span>{cb.recipe_count} recettes</span>
                {cb.my_role && <span className="badge">{cb.my_role}</span>}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="card p-8 text-center text-charcoal-500">Aucun cookbook. Creez-en un pour partager vos recettes.</div>
      )}
      {list.data && list.data.length > PAGE_SIZE && (
        <div className="flex justify-center pt-2">
          <button onClick={() => setPage((p) => p + 1)} disabled={!hasMore} className="btn-outline">
            {hasMore ? "Charger plus" : "Fin"}
          </button>
        </div>
      )}
    </div>
  );
}