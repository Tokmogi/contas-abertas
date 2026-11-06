"""Proteção contra CSRF: impede que outro site envie formulários em nome do usuário logado."""
import secrets

from flask import abort, request, session


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def conferir_csrf(app) -> None:
    @app.before_request
    def _conferir():
        if request.method != "POST" or not app.config.get("CSRF_ATIVO", True):
            return
        enviado = request.form.get("csrf_token", "")
        esperado = session.get("csrf_token", "")
        if not esperado or not secrets.compare_digest(enviado.encode(), esperado.encode()):
            abort(400, "Formulário expirado. Volte, recarregue a página e tente de novo.")

    @app.after_request
    def _cabecalhos(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")  # evita clickjacking
        resposta.headers.setdefault("Referrer-Policy", "same-origin")
        return resposta

    app.jinja_env.globals["csrf_token"] = csrf_token
