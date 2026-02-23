import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseKey);

if (import.meta.env.DEV) {
  const maskedKey = supabaseKey
    ? `${supabaseKey.slice(0, 6)}...${supabaseKey.slice(-4)}`
    : "missing";
  console.log("Supabase config:", {
    url: supabaseUrl ?? "missing",
    key: maskedKey,
  });
}

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl!, supabaseKey!)
  : null;
