def capture_exception(error=None, scope=None, **scope_kwargs):
    try:
        from sentry_sdk import capture_exception
    except ImportError:
        pass
    else:
        capture_exception(error, scope, **scope_kwargs)
