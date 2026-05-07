"""Typed error codes for LLM/AI pipeline.

Used by SSE error frames, the orchestrator's enhancement_status (when
unavailable_failed), and the provider manager's error context.

Finding #6 permanent + Findings B13/B14: replace ad-hoc string error
messages with a small enum so frontend can branch and ops can monitor.
"""


class AIErrorCode:
    AUTH_ERROR = "auth_error"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    BAD_REQUEST = "bad_request"
    UNKNOWN = "unknown"


def classify_anthropic_error(exc):
    """Map an anthropic.* exception (or generic Exception) to an AIErrorCode.

    Falls back to AIErrorCode.UNKNOWN when the anthropic SDK is not
    installed or the exception type is unrecognized.
    """
    try:
        import anthropic
    except ImportError:
        return AIErrorCode.UNKNOWN

    if isinstance(exc, anthropic.AuthenticationError):
        return AIErrorCode.AUTH_ERROR
    if isinstance(exc, anthropic.RateLimitError):
        return AIErrorCode.RATE_LIMITED
    if isinstance(exc, anthropic.APIConnectionError):
        return AIErrorCode.SERVICE_UNAVAILABLE
    if isinstance(exc, anthropic.BadRequestError):
        return AIErrorCode.BAD_REQUEST
    return AIErrorCode.UNKNOWN


USER_FACING_MESSAGES = {
    AIErrorCode.AUTH_ERROR: "AI authentication failed. Check the API key in Settings.",
    AIErrorCode.RATE_LIMITED: "AI service is rate limited. Try again in a moment.",
    AIErrorCode.SERVICE_UNAVAILABLE: "AI service is temporarily unavailable.",
    AIErrorCode.BAD_REQUEST: "AI request was rejected. Check input length / model name.",
    AIErrorCode.UNKNOWN: "AI service error. See server logs.",
}
