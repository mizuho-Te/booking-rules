"""Read-only resource booking rules."""
from .core import MAX_BUFFER_MINUTES, MAX_RECORDS, ValidationError, evaluate

__all__ = ['evaluate', 'ValidationError', 'MAX_RECORDS', 'MAX_BUFFER_MINUTES']
__version__ = '0.1.0'
