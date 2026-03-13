# services/cookie_session.py
# Persistencia de sesión usando cookies del navegador — SOLUCIÓN ROBUSTA v2
#
# ─── PROBLEMA ORIGINAL ────────────────────────────────────────────────────────
# La versión anterior intentaba leer la cookie via st.query_params["_lp_sess"],
# pero NUNCA se inyectaba el JavaScript que leía la cookie y la ponía en
# query_params. Resultado: la sesión no se podía restaurar tras reinicios del
# servidor Railway, causando logouts cada ~3 minutos.
#
# ─── SOLUCIÓN v2 ──────────────────────────────────────────────────────────────
# Usamos streamlit-cookies-controller que implementa correctamente el puente
# JS ↔ Python mediante st.components.v1.declare_component().
# Para evitar el rerun extra (condición de carrera), inicializamos el controller
# UNA SOLA VEZ por sesión y guardamos las cookies en st.session_state.
#
# ─── FLUJO ────────────────────────────────────────────────────────────────────
# LOGIN:  save_session_cookie()       → escribe cookie via CookieController.set()
# RERUN:  restore_session_from_cookie() → lee cookie via CookieController.get()
# LOGOUT: delete_session_cookie()     → borra cookie via CookieController.remove()

import streamlit as st
import hashlib
import time
import json
import os
from datetime import datetime

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


# ── Cookie Controller (singleton por sesión) ─────────────────────────────────
def _get_cookie_controller():
    """
    Retorna el CookieController, inicializándolo solo una vez por sesión.
    Guarda las cookies en st.session_state para evitar reruns extra.
    """
    try:
        from streamlit_cookies_controller import CookieController
        # Usar una clave única para no interferir con otros componentes
        if '_lp_cookie_ctrl' not in st.session_state:
            ctrl = CookieController(key='_lp_cookie_ctrl')
            # Las cookies se cargan en el primer rerun; guardar referencia
            st.session_state['_lp_cookie_ctrl_obj'] = ctrl
        else:
            ctrl = st.session_state.get('_lp_cookie_ctrl_obj')
            if ctrl is None:
                ctrl = CookieController(key='_lp_cookie_ctrl')
                st.session_state['_lp_cookie_ctrl_obj'] = ctrl
        return ctrl
    except ImportError:
        print("[CookieSession] streamlit-cookies-controller no disponible, usando fallback")
        return None
    except Exception as e:
        print(f"[CookieSession] Error al inicializar CookieController: {e}")
        return None


# ── API pública ───────────────────────────────────────────────────────────────
def save_session_cookie(user_id: int, username: str, role: str, full_name: str):
    """
    Guarda la sesión del usuario en una cookie del navegador.
    Se llama después de un login exitoso.
    """
    try:
        import base64
        token        = _generate_token(user_id, username)
        session_data = json.dumps({
            "token":     token,
            "role":      role,
            "full_name": full_name
        })
        max_age_seconds = int(SESSION_HOURS * 3600)
        encoded_val = base64.b64encode(session_data.encode()).decode()

        ctrl = _get_cookie_controller()
        if ctrl is not None:
            # Usar CookieController para escribir la cookie
            from datetime import timedelta
            ctrl.set(
                COOKIE_NAME,
                encoded_val,
                max_age=max_age_seconds,
                path='/',
                same_site='lax'
            )
            print(f"[CookieSession] Cookie guardada (controller) para: {username}")
        else:
            # Fallback: usar components.html con script
            _save_cookie_fallback(encoded_val, max_age_seconds)
            print(f"[CookieSession] Cookie guardada (fallback) para: {username}")

    except Exception as e:
        print(f"[CookieSession] No se pudo guardar cookie: {e}")
        # Intentar fallback
        try:
            import base64
            token = _generate_token(user_id, username)
            session_data = json.dumps({"token": token, "role": role, "full_name": full_name})
            encoded_val = base64.b64encode(session_data.encode()).decode()
            _save_cookie_fallback(encoded_val, int(SESSION_HOURS * 3600))
        except Exception as e2:
            print(f"[CookieSession] Fallback también falló: {e2}")


def _save_cookie_fallback(encoded_val: str, max_age_seconds: int):
    """Fallback: guarda cookie usando components.html (el script SÍ se ejecuta en iframe)."""
    import streamlit.components.v1 as components
    js_code = f"""
    <script>
    (function() {{
        document.cookie = '{COOKIE_NAME}=' + '{encoded_val}' +
            '; Max-Age={max_age_seconds}' +
            '; path=/' +
            '; SameSite=Lax';
        // Notificar al padre (Streamlit) que la cookie fue guardada
        window.parent.postMessage({{type: 'lp_cookie_saved'}}, '*');
    }})();
    </script>
    """
    components.html(js_code, height=0, scrolling=False)


def restore_session_from_cookie() -> bool:
    """
    Intenta restaurar la sesión desde la cookie del navegador.
    Usa CookieController para leer la cookie de forma confiable.

    Returns:
        True si se restauró (o ya estaba activa) la sesión.
        False si no hay cookie válida.
    """
    # Si ya hay sesión activa en memoria, no hacer nada
    if st.session_state.get("logged_in", False):
        return True

    try:
        from database.db_manager import DBManager
        import base64

        # Intentar leer con CookieController
        raw_cookie = None
        ctrl = _get_cookie_controller()
        if ctrl is not None:
            try:
                raw_cookie = ctrl.get(COOKIE_NAME)
            except Exception as e:
                print(f"[CookieSession] Error leyendo cookie con controller: {e}")

        # Fallback: leer desde query_params (por si se puso manualmente)
        if not raw_cookie:
            raw_cookie = st.query_params.get("_lp_sess", None)

        if not raw_cookie:
            return False

        # Decodificar base64
        try:
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
        ctrl = _get_cookie_controller()
        if ctrl is not None:
            try:
                ctrl.remove(COOKIE_NAME, path='/')
                print("[CookieSession] Cookie eliminada (controller).")
            except Exception as e:
                print(f"[CookieSession] Error eliminando con controller: {e}")
                _delete_cookie_fallback()
        else:
            _delete_cookie_fallback()

        # Limpiar el controller del session_state para que se reinicialice
        for key in ['_lp_cookie_ctrl', '_lp_cookie_ctrl_obj']:
            if key in st.session_state:
                del st.session_state[key]

    except Exception as e:
        print(f"[CookieSession] No se pudo eliminar cookie: {e}")


def _delete_cookie_fallback():
    """Fallback: elimina cookie usando components.html."""
    import streamlit.components.v1 as components
    js_code = f"""
    <script>
    (function() {{
        document.cookie = '{COOKIE_NAME}=; Max-Age=0; path=/; SameSite=Lax';
    }})();
    </script>
    """
    components.html(js_code, height=0, scrolling=False)
