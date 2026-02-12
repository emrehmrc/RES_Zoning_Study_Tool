"""
Base class for application tabs
"""
from abc import ABC, abstractmethod
import streamlit as st


class BaseTab(ABC):
    """
    Abstract base class for application tabs
    """
    
    def __init__(self, session_state):
        """
        Initialize tab with session state
        
        Parameters:
        -----------
        session_state : streamlit.SessionState
            Shared session state object
        """
        self.state = session_state
    
    @abstractmethod
    def render(self):
        """
        Render the tab content (must be implemented by subclasses)
        """
        pass
    
    @abstractmethod
    def validate(self):
        """
        Validate tab inputs before allowing progression
        
        Returns:
        --------
        bool : True if valid, False otherwise
        """
        pass
    
    def can_proceed(self):
        """
        Check if user can proceed to next tab
        
        Returns:
        --------
        bool : True if validation passes
        """
        return self.validate()