import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "http://localhost:8000"; // fallback
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "anon";

export const supabase = createClient(supabaseUrl, supabaseKey);
