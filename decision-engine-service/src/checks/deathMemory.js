/**
 * CHECK 2: Death Memory
 * 
 * Purpose: Prevent repetition of dead ideas
 * Rule: If Idea or its cluster is marked as DEAD → REJECT
 */
export function deathMemory(idea, deathMemory) {
  // MVP: Check idea status
  if (idea.status === 'dead') {
    return {
      name: 'death_memory',
      result: 'FAILED',
      details: {
        reason: 'idea_marked_as_dead',
        idea_id: idea.id
      }
    };
  }

  // Future: Check cluster death status
  // if (deathMemory?.cluster_dead) {
  //   return { result: 'FAILED', ... };
  // }

  return {
    name: 'death_memory',
    result: 'PASSED',
    details: {}
  };
}

