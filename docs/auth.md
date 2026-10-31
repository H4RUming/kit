# Login and secrets
- Read passwords and keys from environment variables only. Never hardcode them, never write them to files, never print them. To check presence use `test -n "$NAME" && echo set`.
- In webchecks.json reference secrets as `"{env:NAME}"` (masked as *** in output). Cookies persist between checks, so login flows can be verified over HTTP even when the Browser preview blocks cookies.
- In pytest, test login with the framework test client (Flask `app.test_client()`, FastAPI `TestClient`) and set secrets with `monkeypatch.setenv`, so tests do not depend on the real environment.
- If login does not persist in the Browser preview, the likely cause is that the preview is embedded from another domain and the browser treats the session cookie as third-party. Explain this to the user. Do not weaken cookie settings (e.g. `SameSite=None`) without asking.
