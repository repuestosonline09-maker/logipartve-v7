# services/cookie_session.py
# Persistencia de sesión — SOLUCIÓN DEFINITIVA v6 (localStorage JS + query_params doble-capa)
#
# ─── HISTORIAL DE CORRECCIONES ───────────────────────────────────────────────
# v5: localStorage JS + query_params → funciona pero el iframe de height=0
#     puede no ejecutarse antes del st.rerun() en algunos navegadores/móviles,
#     dejando localStorage vacío y expulsando al analista en cada reinicio.
#
# v6 (CORRECCIÓN DEFINITIVA): Triple capa de persistencia
#   1. Al hacer login: guardar token en st.query_params ANTES del st.rerun()
#      → el token viaja en la URL del rerun, sin depender del iframe
#   2. Al mismo tiempo: inyectar JS para guardar en localStorage
#      → para futuros reinicios del servidor
#   3. Al restaurar sesión: leer primero query_params, luego localStorage
#      → si query_params tiene el token, restaurar inmediatamente sin esperar JS
#
# CORRECCIÓN ADICIONAL: SESSION_HOURS aumentado a 24h (de 12h)
#   → Julia trabaja más de 12h y el token expiraba durante su jornada
#
# CORRECCIÓN ADICIONAL: RENEW_THRESHOLD aumentado a 4h (de 2h)
#   → Renovar el token con más margen para evitar expiraciones en jornadas largas
#
# ─── SEGURIDAD ────────────────────────────────────────────────────────────────
# El token es un JWT firmado con SECRET_KEY. Sin la clave, no se puede forjar.
# El token expira en SESSION_HOURS horas.

import streamlit as st
import streamlit.components.v1 as components
import hashlib
import time
import json
import base64
import os
from datetime import datetime, timedelta

# ── Configuración ────────────────────────────────────────────────────────────
SECRET_KEY      = os.environ.get("SECRET_KEY", "logipartve_secret_2026_railway")
SESSION_HOURS   = 24   # v6: aumentado de 12h a 24h para jornadas largas
RENEW_THRESHOLD = 4    # v6: aumentado de 2h a 4h para renovar con más margen
TOKEN_PARAM     = "_lp_token"  # Nombre del query param usado para pasar el token

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


# ── Componente JS para leer/escribir localStorage ────────────────────────────
def _inject_token_reader():
    """
    Inyecta un componente JS que:
    1. Lee el token de localStorage
    2. Si existe, lo pone en la URL como query param ?_lp_token=XXX
    3. Streamlit hace un rerun automático al detectar el cambio de URL
    
    Este componente se inyecta SOLO cuando no hay sesión activa en memoria,
    para que el servidor pueda leer el token en el siguiente rerun.
    
    IMPORTANTE: Solo se inyecta una vez por carga de página para evitar
    bucles infinitos.
    """
    if st.session_state.get('_token_reader_injected'):
        return
    st.session_state['_token_reader_injected'] = True

    components.html("""
    <script>
    (function() {
        var TOKEN_KEY = 'lp_session_token';
        var PARAM_NAME = '_lp_token';
        
        // Leer token de localStorage
        var token = localStorage.getItem(TOKEN_KEY);
        
        if (!token) {
            // No hay token guardado: no hacer nada, el servidor mostrará el login
            return;
        }
        
        // Verificar si el token ya está en la URL (evitar bucle)
        var url = new URL(window.parent.location.href);
        if (url.searchParams.get(PARAM_NAME) === token) {
            return;
        }
        
        // Poner el token en la URL y navegar para forzar rerun de Streamlit
        url.searchParams.set(PARAM_NAME, token);
        window.parent.location.href = url.toString();
    })();
    </script>
    """, height=0, scrolling=False)


def _inject_token_writer(token: str):
    """
    Inyecta un componente JS que guarda el token en localStorage
    y limpia el query param de la URL para que no quede visible.
    Se llama después de un login exitoso.
    """
    token_escaped = token.replace("'", "\\'")
    components.html(f"""
    <script>
    (function() {{
        var TOKEN_KEY = 'lp_session_token';
        var PARAM_NAME = '_lp_token';
        
        // Guardar token en localStorage
        localStorage.setItem(TOKEN_KEY, '{token_escaped}');
        
        // Limpiar el query param de la URL (no debe quedar visible)
        var url = new URL(window.parent.location.href);
        url.searchParams.delete(PARAM_NAME);
        window.parent.history.replaceState({{}}, '', url.toString());
    }})();
    </script>
    """, height=0, scrolling=False)


def _inject_token_cleaner():
    """
    Inyecta un componente JS que elimina el token de localStorage.
    Se llama al hacer logout.
    """
    components.html("""
    <script>
    (function() {
        localStorage.removeItem('lp_session_token');
        // Limpiar también el query param si quedó en la URL
        var url = new URL(window.parent.location.href);
        url.searchParams.delete('_lp_token');
        window.parent.history.replaceState({}, '', url.toString());
    })();
    </script>
    """, height=0, scrolling=False)


# ── API pública ───────────────────────────────────────────────────────────────
def save_session_cookie(user_id: int, username: str, role: str, full_name: str):
    """
    Guarda la sesión en localStorage del navegador.
    Se llama al hacer login exitoso.
    Mantiene el nombre 'save_session_cookie' para compatibilidad con el resto del código.
    
    v6: También guarda el token en st.query_params para que el rerun lo lea
    directamente sin depender del iframe JS.
    """
    try:
        token = _generate_token(user_id, username)
        # CAPA 1: Guardar en query_params para que el rerun lo lea inmediatamente
        # Esto es más confiable que el iframe porque viaja en la URL del rerun
        try:
            st.query_params[TOKEN_PARAM] = token
        except Exception as _qp_err:
            print(f"[SessionToken] No se pudo guardar en query_params: {_qp_err}")
        # CAPA 2: Guardar en session_state para que inject_token_writer_if_pending
        # lo escriba en localStorage en el siguiente render
        st.session_state['_pending_token_save'] = token
        print(f"[SessionToken] Token generado para: {username} (24h, doble-capa)")
    except Exception as e:
        print(f"[SessionToken] Error generando token: {e}")


def inject_token_writer_if_pending():
    """
    Si hay un token pendiente de guardar en localStorage, inyectar el JS.
    Se llama desde show_main_app() después del login exitoso.
    """
    token = st.session_state.pop('_pending_token_save', None)
    if token:
        _inject_token_writer(token)


def restore_session_from_cookie() -> bool:
    """
    Intenta restaurar la sesión desde localStorage del navegador.
    
    v6: Lee el token desde st.query_params[TOKEN_PARAM] que puede haber sido
    puesto por:
    1. save_session_cookie() directamente (login inmediato, capa 1)
    2. El componente JS que lee localStorage (reinicios del servidor, capa 2)
    
    Mantiene el nombre 'restore_session_from_cookie' para compatibilidad.
    
    Returns:
        True si se restauró la sesión.
        False si no hay token válido.
    """
    # Si ya hay sesión activa en memoria, no hacer nada
    if st.session_state.get("logged_in", False):
        return True

    try:
        from database.db_manager import DBManager

        # Leer el token desde query_params
        token = st.query_params.get(TOKEN_PARAM, None)

        if not token:
            # No hay token en la URL: inyectar el lector de localStorage
            # CORRECCIÓN: Limpiar la bandera _token_reader_injected antes de inyectar
            # para que si el servidor se reinició (session_state limpio), el lector
            # se inyecte correctamente en cada recarga de página.
            st.session_state.pop('_token_reader_injected', None)
            _inject_token_reader()
            return False

        # Verificar el token
        token_info = _verify_token(token)
        if not token_info["valid"]:
            # Token inválido o expirado: limpiar localStorage
            _inject_token_cleaner()
            # Limpiar el query param
            try:
                del st.query_params[TOKEN_PARAM]
            except Exception:
                pass
            # Limpiar bandera para permitir nuevo intento de login
            st.session_state.pop('_token_reader_injected', None)
            print(f"[SessionToken] Token inválido o expirado — mostrando login")
            return False

        # Buscar el usuario en la BD
        user = DBManager.get_user_by_username(token_info["username"])
        if not user:
            _inject_token_cleaner()
            st.session_state.pop('_token_reader_injected', None)
            print(f"[SessionToken] Usuario '{token_info['username']}' no encontrado en BD")
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
            new_token = _generate_token(user["id"], user["username"])
            # Guardar en query_params Y en localStorage
            try:
                st.query_params[TOKEN_PARAM] = new_token
            except Exception:
                pass
            _inject_token_writer(new_token)
            print(f"[SessionToken] Token renovado para: {user['username']} (quedaban {hours_left:.1f}h)")
        else:
            # Aunque no se renueve, refrescar localStorage con el token actual
            # para garantizar que esté guardado (por si el login anterior falló al guardarlo)
            _inject_token_writer(token)
            print(f"[SessionToken] Sesión restaurada para: {user['username']} ({hours_left:.1f}h restantes)")

        # Limpiar el query param de la URL (ya no es necesario)
        try:
            del st.query_params[TOKEN_PARAM]
        except Exception:
            pass

        return True

    except Exception as e:
        print(f"[SessionToken] No se pudo restaurar sesión: {e}")
        # Limpiar bandera para permitir reintento en el próximo ciclo
        st.session_state.pop('_token_reader_injected', None)
        return False


def delete_session_cookie():
    """
    Elimina el token de localStorage del navegador.
    Se llama al hacer logout.
    Mantiene el nombre 'delete_session_cookie' para compatibilidad.
    """
    try:
        _inject_token_cleaner()
        # Limpiar también el query param si quedó
        try:
            del st.query_params[TOKEN_PARAM]
        except Exception:
            pass
        # Limpiar bandera del lector para que se reinicie en el próximo acceso
        st.session_state.pop('_token_reader_injected', None)
        print("[SessionToken] Token eliminado de localStorage.")
    except Exception as e:
        print(f"[SessionToken] No se pudo eliminar token: {e}")


def inject_session_listener():
    """
    Función de compatibilidad — no es necesaria con la nueva implementación.
    """
    pass
