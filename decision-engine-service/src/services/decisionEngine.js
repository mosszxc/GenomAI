import { randomUUID } from 'crypto';
import { loadIdea, loadSystemState, saveDecision, saveDecisionTrace } from './supabase.js';
import * as checks from '../checks/index.js';

/**
 * Decision Engine — Core decision logic
 */
export const decisionEngine = {
  /**
   * Make decision for an idea
   */
  async makeDecision(input) {
    const { idea_id, idea, system_state, fatigue_state, death_memory } = input;

    // Load idea if not provided
    let ideaData = idea;
    if (!ideaData && idea_id) {
      ideaData = await loadIdea(idea_id);
      if (!ideaData) {
        throw new Error('Idea not found');
      }
    }

    // Load system state if not provided
    let systemState = system_state;
    if (!systemState) {
      systemState = await loadSystemState();
    }

    // Execute checks in fixed order
    const checkResults = [];
    
    // CHECK 1: Schema Validity
    const schemaCheck = checks.schemaValidity(ideaData);
    checkResults.push(schemaCheck);
    if (schemaCheck.result === 'FAILED') {
      return createDecision(ideaData, 'REJECT', checkResults, 'schema_invalid');
    }

    // CHECK 2: Death Memory
    const deathCheck = checks.deathMemory(ideaData, death_memory);
    checkResults.push(deathCheck);
    if (deathCheck.result === 'FAILED') {
      return createDecision(ideaData, 'REJECT', checkResults, 'idea_dead');
    }

    // CHECK 3: Fatigue Constraint (MVP: заглушка)
    const fatigueCheck = checks.fatigueConstraint(ideaData, fatigue_state);
    checkResults.push(fatigueCheck);
    if (fatigueCheck.result === 'FAILED') {
      return createDecision(ideaData, 'REJECT', checkResults, 'fatigue_constraint');
    }

    // CHECK 4: Risk Budget
    const riskCheck = checks.riskBudget(ideaData, systemState);
    checkResults.push(riskCheck);
    if (riskCheck.result === 'FAILED') {
      return createDecision(ideaData, 'DEFER', checkResults, 'risk_budget_exceeded');
    }

    // All checks passed → APPROVE
    return createDecision(ideaData, 'APPROVE', checkResults, null);
  }
};

/**
 * Create Decision and Decision Trace
 */
async function createDecision(idea, decisionType, checkResults, failedCheck) {
  const decisionId = randomUUID();
  const timestamp = new Date().toISOString();

  // Create Decision
  const decision = {
    id: decisionId,
    idea_id: idea.id,
    decision: decisionType.toLowerCase(),
    decision_epoch: 1,
    created_at: timestamp
  };

  // Create Decision Trace
  const decisionTrace = {
    id: randomUUID(),
    decision_id: decisionId,
    checks: checkResults.map((check, index) => ({
      check_name: check.name,
      order: index + 1,
      result: check.result,
      details: check.details || {}
    })),
    result: decisionType,
    created_at: timestamp
  };

  // Save to Supabase
  await saveDecision(decision);
  await saveDecisionTrace(decisionTrace);

  // Return response
  return {
    decision: {
      decision_id: decisionId,
      idea_id: idea.id,
      decision_type: decisionType,
      decision_reason: failedCheck || 'all_checks_passed',
      passed_checks: checkResults.filter(c => c.result === 'PASSED').map(c => c.name),
      failed_checks: checkResults.filter(c => c.result === 'FAILED').map(c => c.name),
      failed_check: failedCheck,
      dominant_constraint: failedCheck,
      cluster_at_decision: idea.active_cluster_id || null,
      horizon: idea.horizon || null,
      system_state: 'exploit', // MVP: фиксированное значение
      policy_version: 'v1.0',
      timestamp: timestamp
    },
    decisionTrace: {
      id: decisionTrace.id,
      decision_id: decisionId,
      checks: decisionTrace.checks,
      result: decisionType,
      created_at: timestamp
    }
  };
}

