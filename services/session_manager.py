# services/session_manager.py
# Gestor de sesión persistente para evitar cierres automáticos

import streamlit as st
import hashlib
import time
from datetime import datetime, timedelta

class SessionManager:
    """
    Gestor de sesión que mantiene la sesión activa y persistente.
    Previene cierres automáticos por timeout de Railway/Streamlit.
    """
    
    SESSION_TIMEOUT_HOURS = 8  # 8 horas de sesión activa
    
    @staticmethod
    def init_session():
        """
        Inicializa el sistema de gestión de sesión.
        Debe llamarse al inicio de la aplicación.
        """
        # Inicializar timestamp de última actividad
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = time.time()
        
        # Inicializar contador de heartbeat
        if 'heartbeat_counter' not in st.session_state:
            st.session_state.heartbeat_counter = 0
    
    @staticmethod
    def update_activity():
        """
        Actualiza el timestamp de última actividad.
        Debe llamarse en cada interacción del usuario.
        """
        st.session_state.last_activity = time.time()
        st.session_state.heartbeat_counter = st.session_state.get('heartbeat_counter', 0) + 1
    
    @staticmethod
    def is_session_expired() -> bool:
        """
        Verifica si la sesión ha expirado por inactividad.
        
        Returns:
            bool: True si la sesión expiró, False si aún está activa
        """
        if 'last_activity' not in st.session_state:
            return True
        
        last_activity = st.session_state.last_activity
        current_time = time.time()
        elapsed_hours = (current_time - last_activity) / 3600
        
        return elapsed_hours > SessionManager.SESSION_TIMEOUT_HOURS
    
    @staticmethod
    def get_session_info() -> dict:
        """
        Obtiene información sobre la sesión actual.
        
        Returns:
            dict: Información de la sesión (tiempo activo, heartbeats, etc.)
        """
        if 'last_activity' not in st.session_state:
            return {
                'active': False,
                'elapsed_time': 0,
                'heartbeats': 0
            }
        
        last_activity = st.session_state.last_activity
        current_time = time.time()
        elapsed_seconds = current_time - last_activity
        
        return {
            'active': True,
            'elapsed_seconds': elapsed_seconds,
            'elapsed_minutes': elapsed_seconds / 60,
            'elapsed_hours': elapsed_seconds / 3600,
            'heartbeats': st.session_state.get('heartbeat_counter', 0),
            'last_activity': datetime.fromtimestamp(last_activity).strftime('%Y-%m-%d %H:%M:%S')
        }
    
    @staticmethod
    def keep_alive():
        """
        Mantiene la sesión activa enviando un heartbeat.
        Debe llamarse periódicamente desde la UI.
        """
        SessionManager.update_activity()
        
        # Inyectar JavaScript para mantener la conexión WebSocket activa
        st.markdown("""
            <script>
            // Mantener conexión WebSocket activa con ping real
            if (window.streamlitKeepAlive === undefined) {
                window.streamlitKeepAlive = setInterval(function() {
                    // Hacer una petición real al servidor para mantener la conexión viva
                    try {
                        var xhr = new XMLHttpRequest();
                        xhr.open('GET', window.location.href, true);
                        xhr.timeout = 5000;
                        xhr.send(null);
                    } catch(e) {}
                }, 45000); // Cada 45 segundos
                console.log('[KeepAlive] Sistema de ping iniciado');
            }
            </script>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def check_and_refresh_session():
        """
        Verifica el estado de la sesión y la refresca si es necesario.
        Previene cierres automáticos.
        """
        # Actualizar actividad
        SessionManager.update_activity()
        
        # Verificar si la sesión está logueada
        if st.session_state.get('logged_in', False):
            # Inyectar código para prevenir timeout del navegador
            st.markdown("""
                <script>
                // Prevenir timeout del navegador
                if (window.preventBrowserTimeout === undefined) {
                    window.preventBrowserTimeout = true;
                    
                    // Detectar cualquier actividad del usuario
                    ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'].forEach(function(event) {
                        document.addEventListener(event, function() {
                            sessionStorage.setItem('lastActivity', Date.now());
                        }, true);
                    });
                    
                    // Mantener sesión activa con ping real al servidor
                    setInterval(function() {
                        try {
                            var xhr = new XMLHttpRequest();
                            xhr.open('GET', window.location.href, true);
                            xhr.timeout = 5000;
                            xhr.send(null);
                        } catch(e) {}
                    }, 45000); // Cada 45 segundos
                }
                </script>
            """, unsafe_allow_html=True)
