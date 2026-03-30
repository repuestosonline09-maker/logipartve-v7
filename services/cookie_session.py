# services/cookie_session.py
# Persistencia de sesión usando cookies del navegador — SOLUCIÓN DEFINITIVA v4
#
# ─── HISTORIA DE PROBLEMAS ────────────────────────────────────────────────────
# v1: Usaba st.markdown() para inyectar JS → los scripts NO se ejecutan en Streamlit
# v2: Usaba CookieController pero mal implementado → en el primer rerun devuelve {}
# v3: Usaba components.html() + postMessage → el iframe está sandboxed, no puede navegar
#
# ─── SOLUCIÓN DEFINITIVA v4 ───────────────────────────────────────────────────
# Usar streamlit-cookies-controller correctamente.
#
# COMPORTAMIENTO CORRECTO de CookieController:
#   - Rerun 1: CookieController() se inicializa, el componente JS carga en el browser
#              y hace un rerun automático de Streamlit
#   - Rerun 2: CookieController.get(COOKIE_NAME) devuelve el valor real de la cookie
#
# FLUJO COMPLETO:
#   Rerun 1: No hay sesión → get_cookie_controller() inicializa el controlador
#            El componente JS hace un rerun automático
#   Rerun 2: get_cookie_controller().get(COOKIE_NAME) tiene el valor → restore_session()
#            Restaura la sesión en st.session_state
#
# NOTA: El usuario puede ver el login por un instante (<1 segundo) antes de que
#       la sesión se restaure. Esto es el comportamiento correcto y esperado.
#
# ─── ESCRITURA DE COOKIE ──────────────────────────────────────────────────────
# Al hacer login: save_session_cookie() usa CookieController.set() que SÍ funciona

import streamlit as st
import hashlib
import time
import json
import base64
import os
from datetime import datetime, timedelta

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


def _get_controller():
    """
    Crea un nuevo CookieController en cada llamada.
    
    IMPORTANTE: NO cachear el controlador en session_state.
    El CookieController necesita crearse en cada rerun para que
    dispare el rerun automático cuando carga las cookies del browser.
    Si se cachea, el segundo rerun no ocurre y las cookies no se leen.
    """
    try:
        from streamlit_cookies_controller import CookieController
        return CookieController(key="_lp_cookies")
    except ImportError:
        print("[CookieSession] streamlit-cookies-controller no disponible")
        return None
    except Exception as e:
        print(f"[CookieSession] Error creando CookieController: {e}")
        return None


# ── API pública ───────────────────────────────────────────────────────────────
def save_session_cookie(user_id: int, username: str, role: str, full_name: str):
    """
    Guarda la sesión en una cookie del navegador.
    Se llama al hacer login exitoso.
    """
    try:
        token = _generate_token(user_id, username)
        session_data = {
            "token":     token,
            "role":      role,
            "full_name": full_name
        }
        session_json = json.dumps(session_data)
        cookie_value = base64.b64encode(session_json.encode()).decode()

        ctrl = _get_controller()
        if ctrl:
            expires = datetime.now() + timedelta(hours=SESSION_HOURS)
            ctrl.set(
                COOKIE_NAME,
                cookie_value,
                expires=expires,
                path="/",
                same_site="lax"
            )
            print(f"[CookieSession] Cookie guardada para: {username}")
        else:
            print("[CookieSession] No se pudo guardar cookie: controlador no disponible")
    except Exception as e:
        print(f"[CookieSession] Error guardando cookie: {e}")


def restore_session_from_cookie() -> bool:
    """
    Intenta restaurar la sesión desde la cookie del navegador.

    FLUJO:
    1. Obtener el CookieController (que en el primer rerun puede devolver {})
    2. Si hay cookie válida → restaurar sesión
    3. Si no hay → esperar el rerun automático del componente

    Returns:
        True si se restauró la sesión.
        False si no hay cookie válida (aún).
    """
    # Si ya hay sesión activa en memoria, no hacer nada
    if st.session_state.get("logged_in", False):
        return True

    try:
        from database.db_manager import DBManager

        ctrl = _get_controller()
        if not ctrl:
            return False

        # Leer la cookie (puede ser None en el primer rerun)
        raw_cookie = ctrl.get(COOKIE_NAME)

        if not raw_cookie:
            # Mostrar mensaje amigable mientras el componente carga la cookie
            # Esto evita que el analista vea la pantalla de login y se confunda
            if not st.session_state.get('_cookie_first_check_done', False):
                st.session_state._cookie_first_check_done = True
                st.info("🔄 Restaurando sesión... un momento por favor.")
            print("[CookieSession] No hay cookie de sesión (o aún no cargó el componente)")
            return False

        # Decodificar base64
        try:
            session_json = base64.b64decode(raw_cookie.encode()).decode()
        except Exception:
            delete_session_cookie()
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
        ctrl = _get_controller()
        if ctrl:
            ctrl.remove(COOKIE_NAME)
            print("[CookieSession] Cookie eliminada del navegador.")
        # Limpiar el controlador del session_state para que se reinicie
        for key in ["_lp_cookie_ctrl", "_lp_cookies"]:
            if key in st.session_state:
                del st.session_state[key]
    except Exception as e:
        print(f"[CookieSession] No se pudo eliminar cookie: {e}")


def inject_session_listener():
    """
    Función de compatibilidad - ya no es necesaria con CookieController.
    El CookieController maneja automáticamente la restauración de sesión.
    """
    pass  # No-op: CookieController maneja esto automáticamente
