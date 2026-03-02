# services/cookie_session.py
# Persistencia de sesión usando cookies del navegador
# Resuelve la pérdida de sesión cuando Railway reinicia el servidor o
# el WebSocket se desconecta brevemente.
#
# SOLUCIÓN AL CIERRE AUTOMÁTICO DE SESIÓN:
# extra_streamlit_components.CookieManager provoca un rerun de Streamlit
# cada vez que se instancia (porque renderiza un componente JavaScript).
# Si se crean 3 instancias distintas (save/restore/delete), se generan
# 3 reruns adicionales por ciclo, lo que puede dejar logged_in=False
# antes de que la cookie se restaure.
#
# Solución: una SOLA instancia de CookieManager, guardada en session_state,
# inicializada una única vez al inicio de la aplicación.

import streamlit as st
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

# ── Configuración ────────────────────────────────────────────────────────────
SECRET_KEY      = os.environ.get("SECRET_KEY", "logipartve_secret_2026_railway")
SESSION_HOURS   = 12   # Duración total de la cookie (horas)
RENEW_THRESHOLD = 2    # Si quedan menos de estas horas, renovar el token

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
        payload      = f"{user_id_str}:{username}:{timestamp_str}"
        expected_sig = hashlib.sha256(f"{payload}:{SECRET_KEY}".encode()).hexdigest()[:16]
        if signature != expected_sig:
            return {"valid": False}
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


# ── Instancia única de CookieManager ─────────────────────────────────────────
def _get_cookie_manager():
    """
    Retorna la instancia única de CookieManager almacenada en session_state.
    Si no existe, la crea una sola vez. Esto evita múltiples reruns por
    instanciación repetida del componente JavaScript.
    """
    if "_lp_cookie_manager" not in st.session_state:
        try:
            import extra_streamlit_components as stx
            st.session_state["_lp_cookie_manager"] = stx.CookieManager(
                key="logipartve_cm_singleton"
            )
        except Exception as e:
            print(f"[CookieSession] No se pudo crear CookieManager: {e}")
            st.session_state["_lp_cookie_manager"] = None
    return st.session_state.get("_lp_cookie_manager")


# ── API pública ───────────────────────────────────────────────────────────────
def save_session_cookie(user_id: int, username: str, role: str, full_name: str):
    """
    Guarda la sesión del usuario en una cookie del navegador.
    Se llama después de un login exitoso.
    """
    try:
        cm = _get_cookie_manager()
        if cm is None:
            return
        token        = _generate_token(user_id, username)
        session_data = json.dumps({
            "token":     token,
            "role":      role,
            "full_name": full_name
        })
        expires_at = datetime.now() + timedelta(hours=SESSION_HOURS)
        cm.set(
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
        from database.db_manager import DBManager
        cm = _get_cookie_manager()
        if cm is None:
            return False
        session_cookie = cm.get("logipartve_session")
        if not session_cookie:
            return False
        try:
            session_data = json.loads(session_cookie)
        except Exception:
            delete_session_cookie()
            return False
        token      = session_data.get("token", "")
        token_info = _verify_token(token)
        if not token_info["valid"]:
            delete_session_cookie()
            return False
        user = DBManager.get_user_by_username(token_info["username"])
        if not user:
            delete_session_cookie()
            return False
        if not user.get("is_active", True):
            delete_session_cookie()
            return False
        # Restaurar sesión en memoria
        st.session_state.logged_in  = True
        st.session_state.user_id    = user["id"]
        st.session_state.username   = user["username"]
        st.session_state.role       = user["role"]
        st.session_state.full_name  = user["full_name"]
        # Renovar el token si está próximo a expirar
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
        cm = _get_cookie_manager()
        if cm is None:
            return
        cm.delete("logipartve_session", key="delete_session_cookie")
        # Limpiar la instancia del manager para forzar recreación en próximo login
        if "_lp_cookie_manager" in st.session_state:
            del st.session_state["_lp_cookie_manager"]
    except Exception as e:
        print(f"[CookieSession] No se pudo eliminar cookie: {e}")
