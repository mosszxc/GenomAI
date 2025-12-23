"""
CHECK 1: Schema Validity

Purpose: Ensure Idea is structurally valid
Rule: If Idea does not fully conform to canonical schema → REJECT
"""


def schema_validity(idea):
    """
    Check if idea conforms to canonical schema
    
    Args:
        idea: Idea object
        
    Returns:
        dict: Check result with 'name', 'result' ('PASSED' or 'FAILED'), and 'details'
    """
    # MVP: Basic validation
    # In production, validate against full canonical schema
    
    if not idea or not idea.get('id'):
        return {
            'name': 'schema_validity',
            'result': 'FAILED',
            'details': {
                'reason': 'idea_missing_or_invalid'
            }
        }
    
    # Check required fields (MVP minimal)
    required_fields = ['id', 'canonical_hash', 'status']
    missing_fields = [field for field in required_fields if not idea.get(field)]
    
    if missing_fields:
        return {
            'name': 'schema_validity',
            'result': 'FAILED',
            'details': {
                'reason': 'missing_required_fields',
                'missing_fields': missing_fields
            }
        }
    
    return {
        'name': 'schema_validity',
        'result': 'PASSED',
        'details': {}
    }

