import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase credentials');
}

export const supabase = createClient(supabaseUrl, supabaseKey, {
  db: {
    schema: 'genomai'
  }
});

/**
 * Load Idea from Supabase
 */
export async function loadIdea(ideaId) {
  const { data, error } = await supabase
    .from('ideas')
    .select('*')
    .eq('id', ideaId)
    .single();

  if (error) {
    throw new Error(`Failed to load idea: ${error.message}`);
  }

  if (!data) {
    return null;
  }

  return data;
}

/**
 * Load System State from Supabase
 */
export async function loadSystemState() {
  // Count active ideas
  const { count, error } = await supabase
    .from('ideas')
    .select('*', { count: 'exact', head: true })
    .eq('status', 'active');

  if (error) {
    throw new Error(`Failed to load system state: ${error.message}`);
  }

  return {
    active_ideas_count: count || 0,
    max_active_ideas: 100, // MVP: фиксированное значение
    current_state: 'exploit' // MVP: фиксированное значение
  };
}

/**
 * Save Decision to Supabase
 */
export async function saveDecision(decision) {
  const { data, error } = await supabase
    .from('decisions')
    .insert(decision)
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to save decision: ${error.message}`);
  }

  return data;
}

/**
 * Save Decision Trace to Supabase
 */
export async function saveDecisionTrace(trace) {
  const { data, error } = await supabase
    .from('decision_traces')
    .insert(trace)
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to save decision trace: ${error.message}`);
  }

  return data;
}

