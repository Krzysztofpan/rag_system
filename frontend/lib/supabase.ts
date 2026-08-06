import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.SUPABASE_URL
const supabaseAnonKey = import.meta.env.SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
    console.warn('SUPABASE_URL or SUPABASE_ANON_KEY is missing — auth will not work.')
}

export const supabase = createClient(supabaseUrl ?? '', supabaseAnonKey ?? '')
