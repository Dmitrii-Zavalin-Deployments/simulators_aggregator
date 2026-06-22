class StepInterface:
    """
    Contract-only interface for the Minimal Step Chain.
    Prohibits unauthorized methods to ensure 100% deterministic execution.
    """
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # CONSTITUTION: Only 'execute' is allowed. 
        # Any helper method must be a standalone utility or a separate step.
        ALLOWED_MEMBERS = {"execute"} 
        
        for name in cls.__dict__:
            if not name.startswith("__") and name not in ALLOWED_MEMBERS:
                raise TypeError(
                    f"CONSTITUTION VIOLATION: Method '{name}' is forbidden in {cls.__name__}. "
                    "All pipeline logic must be contained within 'execute'."
                )

    def execute(self, container):
        """
        Transformation signature of the step.
        Must receive the Sovereign Container (TunerState).
        """
        raise NotImplementedError("Step implementation must override execute().")