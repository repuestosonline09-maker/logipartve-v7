# services/cookie_session.py
# Persistencia de sesión usando cookies del navegador — SOLUCIÓN DEFINITIVA v3
#
# ─── HISTORIA DE PROBLEMAS ────────────────────────────────────────────────────
# v1: Usaba st.markdown() para inyectar JS → los scripts NO se ejecutan
# v2: Usaba CookieController → en el primer rerun devuelve {} (necesita rerun extra)
#
# ─── SOLUCIÓN DEFINITIVA v3 ───────────────────────────────────────────────────
# El mecanismo correcto para leer cookies en Streamlit es:
#
#   1. Al INICIO de la app (antes de mostrar cualquier vista), inyectar con
#      components.html() un script que lea la cookie y la ponga en query_params
#      usando window.parent.history.pushState() o window.parent.postMessage().
#
#   2. En el SIGUIENTE rerun (que el script dispara con window.parent.location.href),
#      leer el valor desde st.query_params["_lp_sess"].
#
# FLUJO CORRECTO:
#   Rerun 1: No hay sesión → inject_cookie_reader() inyecta el JS lector
#            El JS lee la cookie y redirige a /?_lp_sess=<valor>
#   Rerun 2: st.query_params["_lp_sess"] tiene el valor → restore_session()
#            Restaura la sesión y limpia el query_param
#
# ─── ESCRITURA DE COOKIE ──────────────────────────────────────────────────────
# Al hacer login: save_session_cookie() usa components.html() que SÍ ejecuta JS
# El JS escribe la cookie en document.cookie del padre via window.parent

import streamlit as st
import streamlit.components.v1 as components
import hashlib
import time
import json
import os

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
    Usa components.html() que SÍ ejecuta scripts (a diferencia de st.markdown).
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

        # Escribir la cookie en el documento padre (la página principal de Streamlit)
        # El iframe de components.html puede acceder al padre porque es same-origin
        js_code = f"""
        <script>
        (function() {{
            var val = '{encoded_val}';
            var maxAge = {max_age_seconds};
            var cookieName = '{COOKIE_NAME}';
            try {{
                // Escribir en el documento padre
                window.parent.document.cookie = cookieName + '=' + val +
                    '; Max-Age=' + maxAge +
                    '; path=/' +
                    '; SameSite=Lax';
                console.log('[LogiPartVE] Cookie guardada en padre OK');
            }} catch(e) {{
                // Fallback: escribir en el documento local
                document.cookie = cookieName + '=' + val +
                    '; Max-Age=' + maxAge +
                    '; path=/' +
                    '; SameSite=Lax';
                console.log('[LogiPartVE] Cookie guardada local (fallback):', e.message);
            }}
        }})();
        </script>
        """
        components.html(js_code, height=0, scrolling=False)
        print(f"[CookieSession] Cookie guardada para: {username} (expira en {SESSION_HOURS}h)")
    except Exception as e:
        print(f"[CookieSession] No se pudo guardar cookie: {e}")


def inject_cookie_reader():
    """
    Inyecta el JavaScript que lee la cookie del navegador y redirige
    a la misma URL con el parámetro _lp_sess para que Python pueda leerlo.

    DEBE llamarse ANTES de mostrar cualquier vista, cuando no hay sesión activa.
    Solo se inyecta una vez por ciclo (controlado por session_state).
    """
    # Solo inyectar una vez por sesión de Streamlit (no repetir en reruns)
    if st.session_state.get("_lp_reader_injected", False):
        return
    st.session_state["_lp_reader_injected"] = True

    js_code = f"""
    <script>
    (function() {{
        var cookieName = '{COOKIE_NAME}';
        var paramName = '_lp_sess';

        // Leer la cookie del documento padre
        function getCookie(name) {{
            try {{
                var cookies = window.parent.document.cookie;
                var parts = cookies.split(';');
                for (var i = 0; i < parts.length; i++) {{
                    var part = parts[i].trim();
                    if (part.startsWith(name + '=')) {{
                        return part.substring(name.length + 1);
                    }}
                }}
            }} catch(e) {{
                // Si no podemos acceder al padre, intentar con el documento local
                var cookies = document.cookie;
                var parts = cookies.split(';');
                for (var i = 0; i < parts.length; i++) {{
                    var part = parts[i].trim();
                    if (part.startsWith(name + '=')) {{
                        return part.substring(name.length + 1);
                    }}
                }}
            }}
            return null;
        }}

        var cookieVal = getCookie(cookieName);
        if (!cookieVal) {{
            console.log('[LogiPartVE] No hay cookie de sesión');
            return;
        }}

        // Verificar si ya está en los query params (evitar loop)
        try {{
            var parentUrl = new URL(window.parent.location.href);
            if (parentUrl.searchParams.get(paramName)) {{
                console.log('[LogiPartVE] Ya hay _lp_sess en URL, no redirigir');
                return;
            }}

            // Agregar el parámetro a la URL y recargar
            parentUrl.searchParams.set(paramName, cookieVal);
            console.log('[LogiPartVE] Redirigiendo con cookie...');
            window.parent.location.href = parentUrl.toString();
        }} catch(e) {{
            console.log('[LogiPartVE] Error al redirigir:', e.message);
        }}
    }})();
    </script>
    """
    components.html(js_code, height=0, scrolling=False)
    print("[CookieSession] Lector de cookie inyectado")


def restore_session_from_cookie() -> bool:
    """
    Intenta restaurar la sesión desde la cookie del navegador.

    FLUJO:
    1. Si hay _lp_sess en query_params → restaurar sesión directamente
    2. Si no hay → inyectar el JS lector para el siguiente rerun

    Returns:
        True si se restauró (o ya estaba activa) la sesión.
        False si no hay cookie válida (aún).
    """
    # Si ya hay sesión activa en memoria, no hacer nada
    if st.session_state.get("logged_in", False):
        return True

    try:
        from database.db_manager import DBManager
        import base64

        # Intentar leer desde query params (puente JS → Python)
        raw_cookie = st.query_params.get("_lp_sess", None)

        if not raw_cookie:
            # No hay cookie en query_params → inyectar el lector para el próximo rerun
            inject_cookie_reader()
            return False

        # Limpiar el query param para que no quede en la URL
        try:
            st.query_params.pop("_lp_sess", None)
        except Exception:
            pass

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
    Elimina la cookie de sesión del navegador mediante JavaScript.
    Se llama al hacer logout.
    """
    try:
        js_code = f"""
        <script>
        (function() {{
            var cookieName = '{COOKIE_NAME}';
            try {{
                window.parent.document.cookie = cookieName + '=; Max-Age=0; path=/; SameSite=Lax';
                console.log('[LogiPartVE] Cookie eliminada del padre');
            }} catch(e) {{
                document.cookie = cookieName + '=; Max-Age=0; path=/; SameSite=Lax';
                console.log('[LogiPartVE] Cookie eliminada local (fallback)');
            }}
        }})();
        </script>
        """
        components.html(js_code, height=0, scrolling=False)
        # Limpiar el estado del lector
        for key in ['_lp_cycle', '_lp_reader_injected_cycle', '_lp_reader_injected']:
            if key in st.session_state:
                del st.session_state[key]
        print("[CookieSession] Cookie eliminada del navegador.")
    except Exception as e:
        print(f"[CookieSession] No se pudo eliminar cookie: {e}")
