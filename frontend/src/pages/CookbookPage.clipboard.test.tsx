import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CookbookPage from "./CookbookPage";

const apiGet = vi.fn();
const apiPost = vi.fn();
const apiPatch = vi.fn();
const apiDelete = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => apiGet(...args),
    post: (...args: unknown[]) => apiPost(...args),
    patch: (...args: unknown[]) => apiPatch(...args),
    delete: (...args: unknown[]) => apiDelete(...args),
  },
}));

vi.mock("../stores/auth", () => ({
  useAuthStore: (selector: (state: { user: { id: number; username: string; full_name: string | null } }) => unknown) =>
    selector({ user: { id: 1, username: "owner", full_name: "Owner" } }),
}));

vi.mock("../components/RecipeCard", () => ({
  default: () => <div data-testid="recipe-card" />,
}));

function renderCookbookPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/cookbooks/1"]}>
        <Routes>
          <Route path="/cookbooks/:id" element={<CookbookPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("CookbookPage invitation clipboard feedback", () => {
  beforeEach(() => {
    apiPost.mockReset();
    apiPatch.mockReset();
    apiDelete.mockReset();
    apiGet.mockImplementation((url: string) => {
      if (url === "/cookbooks/1") {
        return Promise.resolve({
          data: {
            id: 1,
            name: "Cookbook Test",
            description: "desc",
            image_url: null,
            owner_id: 1,
            members: [
              {
                id: 10,
                role: "creator",
                created_at: "2026-01-01T00:00:00Z",
                user: { id: 1, username: "owner", full_name: "Owner", avatar_url: null },
              },
            ],
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        });
      }
      if (url === "/cookbooks/1/recipes") {
        return Promise.resolve({ data: [] });
      }
      if (url === "/cookbooks/1/invitations") {
        return Promise.resolve({
          data: [
            {
              id: 1,
              cookbook_id: 1,
              invited_email: "guest@example.com",
              invited_role: "reader",
              token: "abc123",
              status: "pending",
              expires_at: "2026-02-01T00:00:00Z",
              invited_by_user_id: 1,
              created_at: "2026-01-01T00:00:00Z",
            },
          ],
        });
      }
      if (url === "/tags") {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("shows success feedback when clipboard copy works", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });

    renderCookbookPage();

    await waitFor(() => {
      expect(screen.getByText("Cookbook Test")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Membres" }));

    await waitFor(() => {
      expect(screen.getByText(/guest@example.com/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Copier" })[0]);

    await waitFor(() => {
      expect(screen.getByText("Lien copie")).toBeInTheDocument();
    });
  });

  it("shows error feedback when clipboard copy fails", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockRejectedValue(new Error("clipboard error")) },
      configurable: true,
    });

    renderCookbookPage();

    await waitFor(() => {
      expect(screen.getByText("Cookbook Test")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Membres" }));

    await waitFor(() => {
      expect(screen.getByText(/guest@example.com/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Copier" })[0]);

    await waitFor(() => {
      expect(screen.getByText("Impossible de copier le lien")).toBeInTheDocument();
    });
  });
});
