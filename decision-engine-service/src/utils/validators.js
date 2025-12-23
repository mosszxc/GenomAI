/**
 * Validate Decision Request
 */
export function validateDecisionRequest(body) {
  if (!body) {
    return 'Request body is required';
  }

  if (!body.idea_id && !body.idea) {
    return 'Either idea_id or idea object is required';
  }

  if (body.idea_id && typeof body.idea_id !== 'string') {
    return 'idea_id must be a string (UUID)';
  }

  if (body.idea && typeof body.idea !== 'object') {
    return 'idea must be an object';
  }

  if (body.idea && !body.idea.id) {
    return 'idea.id is required';
  }

  return null; // Valid
}

