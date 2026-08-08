import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  ChefHat,
  Home,
  BookOpen,
  Calendar,
  Settings,
  LogOut,
  Plus,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Menu,
  X,
} from "lucide-react";
import { useAuthStore } from "../stores/auth";
import { cn } from "../lib/utils";

const navItems = [
  { to: "/", label: "Tableau de bord", icon: Home, end: true },
  { to: "/cookbooks", label: "Mes cookbooks", icon: BookOpen },
  { to: "/planning", label: "Planning", icon: Calendar },
  { to: "/shopping", label: "Courses", icon: ShoppingCart },
  { to: "/suggestions", label: "Suggestions", icon: Sparkles },
  { to: "/settings", label: "Parametres", icon: Settings },
];

export default function Layout() {
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobileMenu = () => setMobileMenuOpen(false);

  const onLogout = () => {
    clear();
    closeMobileMenu();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-cream-50">
      {mobileMenuOpen && (
        <button
          type="button"
          aria-label="Fermer le menu"
          className="fixed inset-0 z-30 bg-black/30 md:hidden"
          onClick={closeMobileMenu}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-60 border-r border-cream-200 bg-white flex flex-col",
          "transform transition-transform duration-200 ease-in-out",
          "md:static md:translate-x-0 md:shrink-0",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center border-b border-cream-200">
          <Link
            to="/"
            onClick={closeMobileMenu}
            className="flex flex-1 items-center gap-2 px-5 py-5"
          >
            <div className="w-9 h-9 rounded-full bg-tomato-500 flex items-center justify-center">
              <ChefHat className="w-5 h-5 text-cream-50" />
            </div>
            <span className="font-display font-bold text-lg text-charcoal-900">
              SUPMEAL
            </span>
          </Link>

          <button
            type="button"
            aria-label="Fermer le menu"
            onClick={closeMobileMenu}
            className="mr-3 rounded p-2 text-charcoal-600 hover:bg-cream-100 md:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={closeMobileMenu}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded text-sm font-medium transition-colors",
                  isActive
                    ? "bg-tomato-100 text-tomato-700"
                    : "text-charcoal-700 hover:bg-cream-100"
                )
              }
            >
              <item.icon className="w-4 h-4 shrink-0" />
              {item.label}
            </NavLink>
          ))}

          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              onClick={closeMobileMenu}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded text-sm font-medium transition-colors",
                  isActive
                    ? "bg-tomato-100 text-tomato-700"
                    : "text-tomato-700 hover:bg-tomato-50"
                )
              }
            >
              <ShieldCheck className="w-4 h-4 shrink-0" />
              Administration
            </NavLink>
          )}
        </nav>

        <div className="border-t border-cream-200 p-3 space-y-2">
          <div className="px-2 py-2">
            <div className="text-sm font-medium text-charcoal-900 truncate">
              {user?.full_name || user?.username}
            </div>
            <div className="text-xs text-charcoal-500 truncate">
              {user?.email}
            </div>
          </div>

          <button
            type="button"
            onClick={onLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded text-sm text-charcoal-700 hover:bg-cream-100"
          >
            <LogOut className="w-4 h-4" />
            Se deconnecter
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="min-h-16 border-b border-cream-200 bg-white flex items-center justify-between gap-3 px-4 py-3 md:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              aria-label="Ouvrir le menu"
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen(true)}
              className="rounded p-2 text-charcoal-700 hover:bg-cream-100 md:hidden"
            >
              <Menu className="w-5 h-5" />
            </button>

            <h1 className="font-display font-semibold text-charcoal-900 text-base sm:text-lg truncate">
              Bonjour, {user?.full_name || user?.username}
            </h1>
          </div>

          <Link
            to="/recipes/new"
            className="btn-primary shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Nouvelle recette</span>
          </Link>
        </header>

        <main className="flex-1 min-w-0 p-4 md:p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
