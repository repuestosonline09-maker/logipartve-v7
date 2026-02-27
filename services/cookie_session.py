# services/cookie_session.py
# Persistencia de sesión usando cookies del navegador
# Esto resuelve el problema de pérdida de sesión cuando Railway reinicia el servidor

import streamlit as st
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

# Clave secreta para firmar tokens de sesión
SECRET_KEY = os.environ.get("SECRET_KEY", "logipartve_secret_2026_railway")

def _generate_token(user_id: int, username: str) -> str:
    """Genera un token de sesión firmado."""
    timestamp = str(int(time.time()))
    payload = f"{user_id}:{username}:{timestamp}"
    signature = hashlib.sha256(f"{payload}:{SECRET_KEY}".encode()).hexdigest()[:16]
    return f"{payload}:{signature}"

def _verify_token(token: str, max_age_hours: int = 8) -> dict:
    """
    Verifica un token de sesión.
    Returns dict con {valid, user_id, username} o {valid: False}
    """
    try:
        parts = token.split(":")
        if len(parts) != 4:
            return {"valid": False}
        
        user_id_str, username, timestamp_str, signature = parts
        
        # Verificar firma
        payload = f"{user_id_str}:{username}:{timestamp_str}"
        expected_sig = hashlib.sha256(f"{payload}:{SECRET_KEY}".encode()).hexdigest()[:16]
        if signature != expected_sig:
            return {"valid": False}
        
        # Verificar expiración
        token_time = int(timestamp_str)
        elapsed_hours = (time.time() - token_time) / 3600
        if elapsed_hours > max_age_hours:
            return {"valid": False}
        
        return {
            "valid": True,
            "user_id": int(user_id_str),
            "username": username
        }
    except Exception:
        return {"valid": False}


def save_session_cookie(user_id: int, username: str, role: str, full_name: str):
    """
    Guarda la sesión del usuario en una cookie del navegador.
    Se llama después de un login exitoso.
    """
    try:
        import extra_streamlit_components as stx
        cookie_manager = stx.CookieManager(key="logipartve_cookie_save")
        
        token = _generate_token(user_id, username)
        session_data = json.dumps({
            "token": token,
            "role": role,
            "full_name": full_name
        })
        
        # Guardar cookie con expiración de 8 horas
        expires_at = datetime.now() + timedelta(hours=8)
        cookie_manager.set(
            "logipartve_session",
            session_data,
            expires_at=expires_at,
            key="set_session_cookie"
        )
    except Exception as e:
        # Si falla, continuar sin cookies (la sesión funcionará normalmente)
        print(f"[CookieSession] No se pudo guardar cookie: {e}")


def restore_session_from_cookie() -> bool:
    """
    Intenta restaurar la sesión desde una cookie del navegador.
    Se llama al inicio de la aplicación.
    
    Returns:
        True si se restauró la sesión, False si no hay cookie válida
    """
    # Si ya hay sesión activa, no hacer nada
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
        
        # Parsear datos de la cookie
        session_data = json.loads(session_cookie)
        token = session_data.get("token", "")
        
        # Verificar token
        token_info = _verify_token(token)
        if not token_info["valid"]:
            # Token inválido o expirado, limpiar cookie
            delete_session_cookie()
            return False
        
        # Obtener datos actualizados del usuario desde la DB
        user = DBManager.get_user_by_username(token_info["username"])
        if not user:
            delete_session_cookie()
            return False
        
        # Restaurar sesión
        st.session_state.logged_in = True
        st.session_state.user_id = user["id"]
        st.session_state.username = user["username"]
        st.session_state.role = user["role"]
        st.session_state.full_name = user["full_name"]
        
        print(f"[CookieSession] Sesión restaurada para: {user['username']}")
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
