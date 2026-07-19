export interface User { id: number; email: string; username: string; full_name: string | null; avatar_url: string | null; role: "user" | "admin"; is_active: boolean; default_servings: number; dietary_preferences: string | null; allergies: string | null; favorite_cuisines: string | null; }
export interface Tag { id: number; name: string; category: string | null; }
export interface Ingredient { id?: number; name: string; quantity?: number | null; unit?: string | null; note?: string | null; position: number; }
export interface Step { id?: number; content: string; position: number; }
export interface RecipeSummary { id: number; title: string; description: string | null; image_url: string | null; prep_time_minutes: number; cook_time_minutes: number; servings: number; is_favorite: boolean; owner_id: number | null; cookbook_id: number | null; tags: Tag[]; created_at: string; updated_at: string; }
export interface Recipe extends RecipeSummary { source_url: string | null; difficulty: string | null; cuisine_type: string | null; is_public: boolean; ingredients: Ingredient[]; steps: Step[]; }
export interface CookbookMember { id: number; user: { id: number; username: string; full_name: string | null; avatar_url: string | null }; role: "creator" | "editor" | "commentator" | "reader"; created_at: string; }
export interface Cookbook { id: number; name: string; description: string | null; image_url: string | null; owner_id: number; members: CookbookMember[]; created_at: string; updated_at: string; }
export interface CookbookSummary { id: number; name: string; description: string | null; image_url: string | null; owner_id: number; member_count: number; recipe_count: number; my_role: "creator" | "editor" | "commentator" | "reader" | null; created_at: string; }
export interface Message { id: number; author_id: number; author?: { id: number; username: string; full_name: string | null; avatar_url: string | null }; content: string; created_at: string; }
export interface MealPlan { id: number; user_id: number; cookbook_id: number | null; recipe_id: number; planned_date: string; meal_slot: "breakfast" | "lunch" | "dinner" | "snack"; servings: number; }
export interface Comment { id: number; recipe_id: number; author_id: number; content: string; created_at: string; }
export interface ShoppingListSummary { id: number; name: string; start_date: string | null; end_date: string | null; is_completed: boolean; created_at: string; }
export interface ShoppingItem { id: number; name: string; quantity: number | null; unit: string | null; is_checked: boolean; }
export interface ShoppingListDetail extends ShoppingListSummary { items: ShoppingItem[]; }