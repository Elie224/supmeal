import { useMutation } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { InvitationAcceptResponse } from "../lib/types";

export default function InvitationAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

  const acceptInvitation = useMutation({
    mutationFn: async () => {
      if (!token) {
        throw new Error("Token manquant");
      }
      return (await api.post<InvitationAcceptResponse>(`/cookbooks/invitations/${token}/accept`)).data;
    },
    onSuccess: (data) => {
      navigate(`/cookbooks/${data.cookbook_id}`, { replace: true });
    },
  });

  return (
    <div className="max-w-xl mx-auto mt-10 card p-6 space-y-4">
      <h1 className="font-display text-xl font-semibold text-charcoal-900">Invitation cookbook</h1>
      <p className="text-sm text-charcoal-600">
        Acceptez cette invitation pour rejoindre le cookbook partage.
      </p>
      {acceptInvitation.isError && (
        <div className="text-sm text-red-600">
          Invitation invalide, expiree ou deja utilisee.
        </div>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          className="btn-primary"
          disabled={acceptInvitation.isPending || !token}
          onClick={() => acceptInvitation.mutate()}
        >
          {acceptInvitation.isPending ? "Acceptation..." : "Accepter l invitation"}
        </button>
        <button
          type="button"
          className="btn-outline"
          onClick={() => navigate("/cookbooks")}
        >
          Retour
        </button>
      </div>
    </div>
  );
}
