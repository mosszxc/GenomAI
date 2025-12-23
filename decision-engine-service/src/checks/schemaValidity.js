/**
 * CHECK 1: Schema Validity
 * 
 * Purpose: Ensure Idea is structurally valid
 * Rule: If Idea does not fully conform to canonical schema → REJECT
 */
export function schemaValidity(idea) {
  // MVP: Basic validation
  // In production, validate against full canonical schema
  
  if (!idea || !idea.id) {
    return {
      name: 'schema_validity',
      result: 'FAILED',
      details: {
        reason: 'idea_missing_or_invalid'
      }
    };
  }

  // Check required fields (MVP minimal)
  const requiredFields = ['id', 'canonical_hash', 'status'];
  const missingFields = requiredFields.filter(field => !idea[field]);

  if (missingFields.length > 0) {
    return {
      name: 'schema_validity',
      result: 'FAILED',
      details: {
        reason: 'missing_required_fields',
        missing_fields: missingFields
      }
    };
  }

  return {
    name: 'schema_validity',
    result: 'PASSED',
    details: {}
  };
}

