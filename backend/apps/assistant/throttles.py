from rest_framework.throttling import ScopedRateThrottle


class AssistantRateThrottle(ScopedRateThrottle):
    """Limit public assistant requests separately from ordinary API traffic."""
