"""
Supabase client and data access functions
"""
from supabase import create_client, Client
import os
from src.utils.errors import SupabaseError


# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(supabase_url, supabase_key)


async def load_idea(idea_id: str) -> dict | None:
    """
    Load Idea from Supabase
    
    Args:
        idea_id: Idea UUID
        
    Returns:
        dict: Idea data or None if not found
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        response = supabase.table('ideas').select('*').eq('id', idea_id).execute()
        
        if not response.data or len(response.data) == 0:
            return None
        
        return response.data[0]
    except Exception as e:
        raise SupabaseError(f"Failed to load idea: {str(e)}")


async def load_system_state() -> dict:
    """
    Load System State from Supabase
    
    Returns:
        dict: System state with active_ideas_count, max_active_ideas, current_state
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        # Count active ideas
        response = supabase.table('ideas').select('id', count='exact').eq('status', 'active').execute()
        
        active_ideas_count = response.count if hasattr(response, 'count') else 0
        
        return {
            'active_ideas_count': active_ideas_count,
            'max_active_ideas': 100,  # MVP: фиксированное значение
            'current_state': 'exploit'  # MVP: фиксированное значение
        }
    except Exception as e:
        raise SupabaseError(f"Failed to load system state: {str(e)}")


async def save_decision(decision: dict) -> dict:
    """
    Save Decision to Supabase
    
    Args:
        decision: Decision object
        
    Returns:
        dict: Saved decision data
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        response = supabase.table('decisions').insert(decision).execute()
        
        if not response.data or len(response.data) == 0:
            raise SupabaseError("Failed to save decision: no data returned")
        
        return response.data[0]
    except Exception as e:
        raise SupabaseError(f"Failed to save decision: {str(e)}")


async def save_decision_trace(trace: dict) -> dict:
    """
    Save Decision Trace to Supabase
    
    Args:
        trace: Decision trace object
        
    Returns:
        dict: Saved trace data
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        response = supabase.table('decision_traces').insert(trace).execute()
        
        if not response.data or len(response.data) == 0:
            raise SupabaseError("Failed to save decision trace: no data returned")
        
        return response.data[0]
    except Exception as e:
        raise SupabaseError(f"Failed to save decision trace: {str(e)}")

