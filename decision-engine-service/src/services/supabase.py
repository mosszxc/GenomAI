"""
Supabase client and data access functions
"""
from supabase import create_client, Client
import os
from src.utils.errors import SupabaseError


# Initialize Supabase client (lazy initialization)
supabase: Client | None = None


def _get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global supabase
    if supabase is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            raise SupabaseError("Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.")
        
        supabase = create_client(supabase_url, supabase_key)
        # Note: Accept-Profile header must be set per-request, not at client level
        # See individual functions for header usage
    return supabase


async def load_idea(idea_id: str) -> dict | None:
    """
    Load Idea from Supabase (schema: genomai)
    
    Args:
        idea_id: Idea UUID
        
    Returns:
        dict: Idea data or None if not found
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        client = _get_supabase_client()
        # Use genomai schema - set header for this request
        # PostgREST requires Accept-Profile header for custom schemas
        response = client.table('ideas').select('*').eq('id', idea_id).execute(
            headers={"Accept-Profile": "genomai"}
        )
        
        if not response.data or len(response.data) == 0:
            return None
        
        return response.data[0]
    except Exception as e:
        raise SupabaseError(f"Failed to load idea: {str(e)}")


async def load_system_state() -> dict:
    """
    Load System State from Supabase (schema: genomai)
    
    Returns:
        dict: System state with active_ideas_count, max_active_ideas, current_state
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        client = _get_supabase_client()
        # Use genomai schema - set header for this request
        # PostgREST requires Accept-Profile header for custom schemas
        response = client.table('ideas').select('id', count='exact').eq('status', 'active').execute(
            headers={"Accept-Profile": "genomai"}
        )
        
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
    Save Decision to Supabase (schema: genomai)
    
    Args:
        decision: Decision object
        
    Returns:
        dict: Saved decision data
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        client = _get_supabase_client()
        # Use genomai schema - set header for this request
        # PostgREST requires Accept-Profile header for custom schemas
        response = client.table('decisions').insert(decision).execute(
            headers={"Accept-Profile": "genomai"}
        )
        
        if not response.data or len(response.data) == 0:
            raise SupabaseError("Failed to save decision: no data returned")
        
        return response.data[0]
    except Exception as e:
        raise SupabaseError(f"Failed to save decision: {str(e)}")


async def save_decision_trace(trace: dict) -> dict:
    """
    Save Decision Trace to Supabase (schema: genomai)
    
    Args:
        trace: Decision trace object
        
    Returns:
        dict: Saved trace data
        
    Raises:
        SupabaseError: If Supabase operation fails
    """
    try:
        client = _get_supabase_client()
        # Use genomai schema - set header for this request
        # PostgREST requires Accept-Profile header for custom schemas
        response = client.table('decision_traces').insert(trace).execute(
            headers={"Accept-Profile": "genomai"}
        )
        
        if not response.data or len(response.data) == 0:
            raise SupabaseError("Failed to save decision trace: no data returned")
        
        return response.data[0]
    except Exception as e:
        raise SupabaseError(f"Failed to save decision trace: {str(e)}")

