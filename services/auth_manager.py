# services/auth_manager.py
# Gestor de autenticación

import bcrypt
import streamlit as st
from database.db_manager import DBManager

class AuthManager:
    """
    Gestor de autenticación que maneja login, logout y sesiones.
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Genera un hash seguro de la contraseña usando bcrypt.
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verifica si una contraseña coincide con su hash.
        """
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    
    @staticmethod
    def login(username: str, password: str) -> dict:
        """
        Autentica a un usuario y lo guarda en la sesión de Streamlit.
        
        Returns:
            dict con {"success": bool, "message": str, "user": User o None}
        """
        try:
            # Buscar usuario
            user = DBManager.get_user_by_username(username)
            
            if not user:
                return {
                    "success": False,
                    "message": "Usuario no encontrado",
                    "user": None
                }
            
            # Verificar contraseña
            if not AuthManager.verify_password(password, user['password_hash']):
                return {
                    "success": False,
                    "message": "Contraseña incorrecta",
                    "user": None
                }
            
            # Login exitoso - guardar en sesión
            st.session_state.logged_in = True
            st.session_state.user_id = user['id']
            st.session_state.username = user['username']
            st.session_state.role = user['role']
            st.session_state.full_name = user['full_name']
            
            # Guardar sesión en cookie para persistencia entre reinicios de Railway
            try:
                from services.cookie_session import save_session_cookie
                save_session_cookie(user['id'], user['username'], user['role'], user['full_name'])
            except Exception:
                pass  # Si falla, la sesión funciona normalmente
            
            # Actualizar último login
            DBManager.update_last_login(user['id'])
            
            # Registrar actividad
            DBManager.log_activity(user['id'], "login", f"Usuario {username} inició sesión")
            
            return {
                "success": True,
                "message": f"¡Bienvenido, {user['full_name']}!",
                "user": user
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Error en el sistema: {str(e)}",
                "user": None
            }
    
    @staticmethod
    def logout():
        """
        Cierra la sesión del usuario.
        """
        try:
            if 'user_id' in st.session_state:
                DBManager.log_activity(st.session_state.user_id, "logout", f"Usuario {st.session_state.username} cerró sesión")
        except:
            pass  # Ignorar errores de logging
        
        # Eliminar cookie de sesión del navegador
        try:
            from services.cookie_session import delete_session_cookie
            delete_session_cookie()
        except Exception:
            pass
        
        # Limpiar SOLO variables de autenticación (no usar clear() que borra todo)
        auth_keys = ['logged_in', 'user_id', 'username', 'role', 'full_name']
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # Asegurar que logged_in esté en False
        st.session_state.logged_in = False
    
    @staticmethod
    def is_logged_in() -> bool:
        """
        Verifica si hay un usuario logueado.
        """
        return st.session_state.get("logged_in", False)
    
    @staticmethod
    def get_current_user() -> dict:
        """
        Devuelve los datos del usuario actual.
        """
        if not AuthManager.is_logged_in():
            return None
        
        return {
            "user_id": st.session_state.get("user_id"),
            "username": st.session_state.get("username"),
            "role": st.session_state.get("role"),
            "full_name": st.session_state.get("full_name")
        }
    
    @staticmethod
    def is_admin() -> bool:
        """
        Verifica si el usuario actual es administrador.
        """
        return st.session_state.get("role") == "admin"
