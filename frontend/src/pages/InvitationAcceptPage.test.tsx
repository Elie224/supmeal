import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InvitationAcceptPage from "./InvitationAcceptPage";

const apiPost = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    post: (...args: unknown[]) => apiPost(...args),
  },
}));

function renderInvitationPage(path = "/invitations/token-123") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/invitations/:token" element={<InvitationAcceptPage />} />
          <Route path="/cookbooks/:id" element={<div data-testid="cookbook-page">Cookbook</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("InvitationAcceptPage", () => {
  beforeEach(() => {
    apiPost.mockReset();
  });

  it("redirects to cookbook on successful acceptance", async () => {
    apiPost.mockResolvedValue({
      data: {
        detail: "Invitation acceptee",
        cookbook_id: 42,
      },
    });

    renderInvitationPage();

    fireEvent.click(screen.getByRole("button", { name: "Accepter l invitation" }));

    await waitFor(() => {
      expect(screen.getByTestId("cookbook-page")).toBeInTheDocument();
    });
    expect(apiPost).toHaveBeenCalledWith("/cookbooks/invitations/token-123/accept");
  });

  it("shows backend detail when acceptance fails", async () => {
    apiPost.mockRejectedValue({
      response: {
        data: {
          detail: "Cette invitation ne vous est pas destinee",
        },
      },
    });

    renderInvitationPage();

    fireEvent.click(screen.getByRole("button", { name: "Accepter l invitation" }));

    await waitFor(() => {
      expect(screen.getByText("Cette invitation ne vous est pas destinee")).toBeInTheDocument();
    });
  });
});
