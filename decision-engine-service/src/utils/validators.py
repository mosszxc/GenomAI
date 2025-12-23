"""
Validation utilities
"""


def validate_decision_request(body: dict) -> str | None:
    """
    Validate Decision Request
    
    Args:
        body: Request body
        
    Returns:
        str: Error message if invalid, None if valid
    """
    if not body:
        return 'Request body is required'
    
    if not body.get('idea_id') and not body.get('idea'):
        return 'Either idea_id or idea object is required'
    
    if body.get('idea_id') and not isinstance(body.get('idea_id'), str):
        return 'idea_id must be a string (UUID)'
    
    if body.get('idea') and not isinstance(body.get('idea'), dict):
        return 'idea must be an object'
    
    if body.get('idea') and not body.get('idea', {}).get('id'):
        return 'idea.id is required'
    
    return None  # Valid

