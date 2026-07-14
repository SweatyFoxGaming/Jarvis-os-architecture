"""
Developer SDK for creating new capabilities.
Provides decorators and helpers.
"""

def capability(manifest):
    def decorator(cls):
        cls._manifest = manifest
        return cls
    return decorator
