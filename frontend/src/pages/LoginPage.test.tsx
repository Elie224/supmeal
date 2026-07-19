import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "./LoginPage";

const mockSetUser = vi.fn();

vi.mock("../stores/auth", () => ({
  useAuthStore: (selector: (state: { setUser: (user: unknown) => void }) => unknown) =>
    selector({ setUser: mockSetUser }),
}));

const apiGet = vi.fn();
const apiPost = vi.fn();

vi.mock("../lib/api", () => ({
  api: {
    get: (...args: unknown[]) => apiGet(...args),
    post: (...args: unknown[]) => apiPost(...args),
  },
}));

function renderLoginWithState(fromPath?: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[
          {
            pathname: "/login",
            state: fromPath ? { from: fromPath } : undefined,
          },
        ]}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div data-testid="home">Home</div>} />
          <Route path="/invitations/:token" element={<div data-testid="invite-page">Invitation</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("LoginPage invitation redirect", () => {
  beforeEach(() => {
    apiGet.mockResolvedValue({ data: { google: false, github: false } });
    apiPost.mockResolvedValue({
      data: {
        user: {
          id: 1,
          email: "invitee@example.com",
          username: "invitee",
          full_name: null,
          avatar_url: null,
        },
      },
    });
    mockSetUser.mockClear();
  });

  it("redirects back to invitation route after successful login", async () => {
    renderLoginWithState("/invitations/token-123");

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "invitee@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "SupMeal!123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    await waitFor(() => {
      expect(screen.getByTestId("invite-page")).toBeInTheDocument();
    });
    expect(mockSetUser).toHaveBeenCalledTimes(1);
  });

  it("redirects to home when no origin route is provided", async () => {
    renderLoginWithState();

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "invitee@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "SupMeal!123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));

    await waitFor(() => {
      expect(screen.getByTestId("home")).toBeInTheDocument();
    });
  });
});
