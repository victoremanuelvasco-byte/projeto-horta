"""Configuração usada somente pelo site publicado."""
import json
import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403

arquivo = BASE_DIR / ".production.json"
configuracao = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}

DEBUG = False
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or configuracao.get("SECRET_KEY", "")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Gere a configuração com python deploy/configurar.py SEU_DOMINIO.")

hosts = os.environ.get("DJANGO_ALLOWED_HOSTS")
ALLOWED_HOSTS = hosts.split(",") if hosts else configuracao.get("ALLOWED_HOSTS", [])
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Configure o domínio exato em ALLOWED_HOSTS.")

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
DATABASES["default"]["OPTIONS"] = {"timeout": 20}
