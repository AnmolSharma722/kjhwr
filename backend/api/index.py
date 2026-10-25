from urllib.parse import parse_qsl, urlencode

from app.main import app as fastapi_app


class VercelPathFix:
    """Vercel rewrites every request to /api/index and passes the real path in ?__p=...
    This puts the real path back before FastAPI routes it."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/api/index"):
            pairs = parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True)
            real = next((v for k, v in pairs if k == "__p"), "")          # original path, e.g. api/health
            rest = [(k, v) for k, v in pairs if k != "__p"]               # the user's own query params (day=...)
            scope = dict(scope)
            scope["path"] = "/" + real.lstrip("/")
            scope["raw_path"] = scope["path"].encode()
            scope["query_string"] = urlencode(rest).encode()
        await self.app(scope, receive, send)


app = VercelPathFix(fastapi_app)  # Vercel looks for a variable named `app`