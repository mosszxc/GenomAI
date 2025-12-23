/**
 * CHECK 4: Risk Budget
 * 
 * Purpose: Control exposure
 * Rule: If max_active_ideas exceeded → DEFER
 * 
 * MVP: Basic risk cap check
 */
export function riskBudget(idea, systemState) {
  const { active_ideas_count, max_active_ideas } = systemState;

  if (active_ideas_count >= max_active_ideas) {
    return {
      name: 'risk_budget',
      result: 'FAILED',
      details: {
        reason: 'max_active_ideas_exceeded',
        active_ideas_count,
        max_active_ideas
      }
    };
  }

  return {
    name: 'risk_budget',
    result: 'PASSED',
    details: {
      active_ideas_count,
      max_active_ideas,
      remaining_slots: max_active_ideas - active_ideas_count
    }
  };
}

