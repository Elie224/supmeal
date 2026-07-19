import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { ChefHat, Home, BookOpen, Calendar, Settings, LogOut, Plus, ShieldCheck, ShoppingCart } from "lucide-react";
import { useAuthStore } from "../stores/auth";
import { cn } from "../lib/utils";

const navItems = [
  { to: "/", label: "Tableau de bord", icon: Home, end: true },
  { to: "/cookbooks", label: "Mes cookbooks", icon: BookOpen },
  { to: "/planning", label: "Planning", icon: Calendar },
  { to: "/shopping", label: "Courses", icon: ShoppingCart },
  { to: "/settings", label: "Parametres", icon: Settings },
];

export default function Layout() {
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();

  const onLogout = () => {
    clear();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-cream-50">
      <aside className="w-60 border-r border-cream-200 bg-white flex flex-col">
        <Link to="/" className="flex items-center gap-2 px-5 py-5 border-b border-cream-200">
          <div className="w-9 h-9 rounded-full bg-tomato-500 flex items-center justify-center">
            <ChefHat className="w-5 h-5 text-cream-50" />
          </div>
          <span className="font-display font-bold text-lg text-charcoal-900">SUPMEAL</span>
        </Link>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded text-sm font-medium transition-colors",
                  isActive
                    ? "bg-tomato-100 text-tomato-700"
                    : "text-charcoal-700 hover:bg-cream-100"
                )
              }
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded text-sm font-medium transition-colors",
                  isActive
                    ? "bg-tomato-100 text-tomato-700"
                    : "text-tomato-700 hover:bg-tomato-50"
                )
              }
            >
              <ShieldCheck className="w-4 h-4" />
              Administration
            </NavLink>
          )}
        </nav>
        <div className="border-t border-cream-200 p-3 space-y-2">
          <div className="px-2 py-2">
            <div className="text-sm font-medium text-charcoal-900 truncate">
              {user?.full_name || user?.username}
            </div>
            <div className="text-xs text-charcoal-500 truncate">{user?.email}</div>
          </div>
          <button
            onClick={onLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded text-sm text-charcoal-700 hover:bg-cream-100"
          >
            <LogOut className="w-4 h-4" />
            Se deconnecter
          </button>
        </div>
      </aside>
      <div className="flex-1 flex flex-col">
        <header className="h-16 border-b border-cream-200 bg-white flex items-center justify-between px-6">
          <h1 className="font-display font-semibold text-charcoal-900 text-lg">
            Bonjour, {user?.full_name || user?.username}
          </h1>
          <Link to="/recipes/new" className="btn-primary">
            <Plus className="w-4 h-4" />
            Nouvelle recette
          </Link>
        </header>
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}