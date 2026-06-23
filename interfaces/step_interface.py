class StepInterface:
    """
    Contract-only interface for pipeline steps.
    Enforces architectural minimalism and guards against arbitrary side-effects.
    """
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # Explicitly define allowed public/internal execution methods; strictly forbid others
        ALLOWED_MEMBERS = {"execute"} 
        
        for name in cls.__dict__:
            # Permit dunder methods (like __init__) but catch unauthorized structural changes
            if not name.startswith("__") and name not in ALLOWED_MEMBERS:
                raise TypeError(
                    f"CONSTITUTION VIOLATION: Class '{cls.__name__}' attempted to register "
                    f"forbidden member attribute or method: '{name}'. Only 'execute' is allowed."
                )

    def execute(self, container) -> None:
        """
        In-place state transformation signature.
        Must accept the Sovereign Container instance exclusively and modify it deterministically.
        """
        raise NotImplementedError("Step implementations must explicitly define an execute method.")