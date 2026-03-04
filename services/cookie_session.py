# services/cookie_session.py
# Persistencia de sesión usando cookies del navegador — SOLUCIÓN NATIVA
#
# ─── POR QUÉ SE ELIMINÓ extra-streamlit-components ───────────────────────────
# extra_streamlit_components.CookieManager renderiza un componente JavaScript
# que provoca un rerun adicional de Streamlit CADA VEZ que se instancia.
# Esto creaba una condición de carrera:
#   1. Analista agrega ítem → st.rerun()
#   2. En el rerun, CookieManager dispara su propio rerun extra
#   3. En ese rerun extra, logged_in puede estar False por un ciclo
#   4. Streamlit muestra la pantalla de login → sesión perdida
#
# ─── SOLUCIÓN ─────────────────────────────────────────────────────────────────
# Usamos st.components.v1.html() para inyectar JavaScript puro que lee y escribe
# document.cookie directamente. Esto NO genera reruns adicionales.
# La cookie se lee mediante st.query_params como puente de comunicación.
#
# ─── FLUJO ────────────────────────────────────────────────────────────────────
# LOGIN:  save_session_cookie()  → inyecta JS que escribe la cookie en el browser
# RERUN:  restore_session_from_cookie() → lee st.query_params["_lp_sess"]
# LOGOUT: delete_session_cookie() → inyecta JS que borra la cookie del browser

import streamlit as st
import streamlit.components.v1 as components
import hashlib
import time
import json
import os
from datetime import datetime, timedelta
from urllib.parse import unquote

# ── Configuración ────────────────────────────────────────────────────────────
SECRET_KEY      = os.environ.get("SECRET_KEY", "logipartve_secret_2026_railway")
SESSION_HOURS   = 12   # Duración total de la cookie (horas)
RENEW_THRESHOLD = 2    # Si quedan menos de estas horas, renovar el token
COOKIE_NAME     = "lp_session"

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


# ── API pública ───────────────────────────────────────────────────────────────
def save_session_cookie(user_id: int, username: str, role: str, full_name: str):
    """
    Guarda la sesión del usuario en una cookie del navegador mediante JavaScript.
    Se llama después de un login exitoso.
    NO genera reruns adicionales de Streamlit.
    """
    try:
        token        = _generate_token(user_id, username)
        session_data = json.dumps({
            "token":     token,
            "role":      role,
            "full_name": full_name
        })
        max_age_seconds = SESSION_HOURS * 3600
        # Codificar el valor para uso seguro en JS (base64-like via encodeURIComponent)
        import base64
        encoded_val = base64.b64encode(session_data.encode()).decode()

        js_code = f"""
        <script>
        (function() {{
            var val = '{encoded_val}';
            document.cookie = '{COOKIE_NAME}=' + val +
                '; Max-Age={max_age_seconds}' +
                '; path=/' +
                '; SameSite=Lax';
        }})();
        </script>
        """
        components.html(js_code, height=0, scrolling=False)
        print(f"[CookieSession] Cookie guardada para: {username} (expira en {SESSION_HOURS}h)")
    except Exception as e:
        print(f"[CookieSession] No se pudo guardar cookie: {e}")


def restore_session_from_cookie() -> bool:
    """
    Intenta restaurar la sesión desde la cookie del navegador.
    Lee el valor desde st.query_params (puesto ahí por el JS de lectura en app.py).
    Si el token está próximo a expirar, lo renueva automáticamente.
    Se llama al inicio de cada rerun de Streamlit.

    Returns:
        True si se restauró (o ya estaba activa) la sesión.
        False si no hay cookie válida.
    """
    # Si ya hay sesión activa en memoria, no hacer nada
    if st.session_state.get("logged_in", False):
        return True

    try:
        from database.db_manager import DBManager

        # Leer desde query params (puente JS → Python)
        raw_cookie = st.query_params.get("_lp_sess", None)

        if not raw_cookie:
            return False

        # Decodificar base64
        try:
            import base64
            session_json = base64.b64decode(raw_cookie.encode()).decode()
        except Exception:
            return False

        try:
            session_data = json.loads(session_json)
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
    Elimina la cookie de sesión del navegador mediante JavaScript.
    Se llama al hacer logout.
    NO genera reruns adicionales de Streamlit.
    """
    try:
        js_code = f"""
        <script>
        (function() {{
            document.cookie = '{COOKIE_NAME}=; Max-Age=0; path=/; SameSite=Lax';
        }})();
        </script>
        """
        components.html(js_code, height=0, scrolling=False)
        # Limpiar el flag del lector para que se reinyecte en el próximo login
        if "_lp_cookie_reader_injected" in st.session_state:
            del st.session_state["_lp_cookie_reader_injected"]
        print("[CookieSession] Cookie eliminada del navegador.")
    except Exception as e:
        print(f"[CookieSession] No se pudo eliminar cookie: {e}")
