import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuthStore } from "./stores/auth";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import RecipePage from "./pages/RecipePage";
import RecipeEditPage from "./pages/RecipeEditPage";
import CookbooksPage from "./pages/CookbooksPage";
import CookbookPage from "./pages/CookbookPage";
import MealPlanPage from "./pages/MealPlanPage";
import ShoppingPage from "./pages/ShoppingPage";
import SettingsPage from "./pages/SettingsPage";
import OAuthCallbackPage from "./pages/OAuthCallbackPage";
import AdminPage from "./pages/AdminPage";
import InvitationAcceptPage from "./pages/InvitationAcceptPage";
import SuggestionsPage from "./pages/SuggestionsPage";
import { type ReactElement } from "react";
import { useEffect } from "react";

function PrivateRoute({ children }: { children: ReactElement }) {
  const isAuth = useAuthStore((s) => s.isAuthenticated);
  const authStatus = useAuthStore((s) => s.authStatus);
  const location = useLocation();
  if (authStatus === "loading") {
    return <div className="min-h-screen grid place-items-center text-charcoal-500">Chargement...</div>;
  }
  if (!isAuth) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/auth/callback" element={<OAuthCallbackPage />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="recipes/:id" element={<RecipePage />} />
        <Route path="recipes/:id/edit" element={<RecipeEditPage />} />
        <Route path="recipes/new" element={<RecipeEditPage />} />
        <Route path="cookbooks" element={<CookbooksPage />} />
        <Route path="cookbooks/:id" element={<CookbookPage />} />
        <Route path="invitations/:token" element={<InvitationAcceptPage />} />
        <Route path="planning" element={<MealPlanPage />} />
        <Route path="shopping" element={<ShoppingPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="suggestions" element={<SuggestionsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
