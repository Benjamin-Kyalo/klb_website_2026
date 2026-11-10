from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Return consistent, front-end friendly error payloads.

    The React client can rely on ``{"detail": "..."}`` or ``{"errors": {...}}``.
    """
    response = exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    if isinstance(data, dict) and "detail" in data:
        response.data = {"detail": str(data["detail"])}
    else:
        response.data = {"detail": "Please check the highlighted fields.", "errors": data}
    return response
