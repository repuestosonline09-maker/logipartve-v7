# services/cookie_session.py
# Persistencia de sesión usando cookies del navegador
# Resuelve la pérdida de sesión cuando Railway reinicia el servidor o
# el WebSocket se desconecta brevemente.

import streamlit as st
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

# ── Configuración ────────────────────────────────────────────────────────────
SECRET_KEY        = os.environ.get("SECRET_KEY", "logipartve_secret_2026_railway")
SESSION_HOURS     = 12   # Duración total de la cookie (horas)
RENEW_THRESHOLD   = 2    # Si quedan menos de estas horas, renovar el token automáticamente


# ── Helpers de token ─────────────────────────────────────────────────────────

def _generate_token(user_id: int, username: str) -> str:
    """Genera un token de sesión firmado con timestamp."""
    timestamp = str(int(time.time()))
    payload   = f"{user_id}:{username}:{timestamp}"
    signature = hashlib.sha256(f"{payload}:{SECRET_KEY}".encode()).hexdigest()[:16]
    return f"{payload}:{signature}"


def _verify_token(token: str, max_age_hours: int = SESSION_HOURS) -> dict:
    """
    Verifica un token de sesión.
    Returns dict con {valid, user_id, username, elapsed_hours} o {valid: False}
    """
    try:
        parts = token.split(":")
        if len(parts) != 4:
            return {"valid": False}

        user_id_str, username, timestamp_str, signature = parts

        # Verificar firma
        payload      = f"{user_id_str}:{username}:{timestamp_str}"
        expected_sig = hashlib.sha256(f"{payload}:{SECRET_KEY}".encode()).hexdigest()[:16]
        if signature != expected_sig:
            return {"valid": False}

        # Verificar expiración
        token_time    = int(timestamp_str)
        elapsed_hours = (time.time() - token_time) / 3600
        if elapsed_hours > max_age_hours:
            return {"valid": False}

        return {
            "valid":         True,
            "user_id":       int(user_id_str),
            "username":      username,
            "elapsed_hours": elapsed_hours
        }
    except Exception:
        return {"valid": False}


# ── API pública ───────────────────────────────────────────────────────────────

def save_session_cookie(user_id: int, username: str, role: str, full_name: str):
    """
    Guarda la sesión del usuario en una cookie del navegador.
    Se llama después de un login exitoso.
    """
    try:
        import extra_streamlit_components as stx
        cookie_manager = stx.CookieManager(key="logipartve_cookie_save")

        token        = _generate_token(user_id, username)
        session_data = json.dumps({
            "token":     token,
            "role":      role,
            "full_name": full_name
        })

        expires_at = datetime.now() + timedelta(hours=SESSION_HOURS)
        cookie_manager.set(
            "logipartve_session",
            session_data,
            expires_at=expires_at,
            key="set_session_cookie"
        )
        print(f"[CookieSession] Cookie guardada para: {username} (expira en {SESSION_HOURS}h)")
    except Exception as e:
        print(f"[CookieSession] No se pudo guardar cookie: {e}")


def restore_session_from_cookie() -> bool:
    """
    Intenta restaurar la sesión desde una cookie del navegador.
    Si el token está próximo a expirar, lo renueva automáticamente.
    Se llama al inicio de cada rerun de Streamlit.

    Returns:
        True si se restauró (o ya estaba activa) la sesión, False si no hay cookie válida.
    """
    # Si ya hay sesión activa en memoria, no hacer nada
    if st.session_state.get("logged_in", False):
        return True

    try:
        import extra_streamlit_components as stx
        from database.db_manager import DBManager

        cookie_manager = stx.CookieManager(key="logipartve_cookie_restore")

        # Obtener cookie
        session_cookie = cookie_manager.get("logipartve_session")
        if not session_cookie:
            return False

        # Parsear datos
        try:
            session_data = json.loads(session_cookie)
        except Exception:
            delete_session_cookie()
            return False

        token      = session_data.get("token", "")
        token_info = _verify_token(token)

        if not token_info["valid"]:
            # Token inválido o expirado — limpiar y pedir nuevo login
            delete_session_cookie()
            return False

        # Obtener datos actualizados del usuario desde la BD
        user = DBManager.get_user_by_username(token_info["username"])
        if not user:
            delete_session_cookie()
            return False

        # Verificar que el usuario siga activo
        if not user.get("is_active", True):
            delete_session_cookie()
            return False

        # Restaurar sesión en memoria
        st.session_state.logged_in  = True
        st.session_state.user_id    = user["id"]
        st.session_state.username   = user["username"]
        st.session_state.role       = user["role"]
        st.session_state.full_name  = user["full_name"]

        # Renovar el token si está próximo a expirar (menos de RENEW_THRESHOLD horas)
        hours_left = SESSION_HOURS - token_info["elapsed_hours"]
        if hours_left < RENEW_THRESHOLD:
            save_session_cookie(user["id"], user["username"], user["role"], user["full_name"])
            print(f"[CookieSession] Token renovado para: {user['username']} (quedaban {hours_left:.1f}h)")
        else:
            print(f"[CookieSession] Sesión restaurada para: {user['username']} ({hours_left:.1f}h restantes)")

        return True

    except Exception as e:
        print(f"[CookieSession] No se pudo restaurar sesión: {e}")
        return False


def delete_session_cookie():
    """
    Elimina la cookie de sesión del navegador.
    Se llama al hacer logout.
    """
    try:
        import extra_streamlit_components as stx
        cookie_manager = stx.CookieManager(key="logipartve_cookie_delete")
        cookie_manager.delete("logipartve_session", key="delete_session_cookie")
    except Exception as e:
        print(f"[CookieSession] No se pudo eliminar cookie: {e}")
