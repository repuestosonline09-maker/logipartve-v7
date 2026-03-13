# services/session_manager.py
# Gestor de sesión persistente para evitar cierres automáticos en Railway
#
# CORRECCIÓN v2: El keep-alive ahora usa components.html() en lugar de
# st.markdown(). Los scripts en st.markdown() NO se ejecutan en Streamlit
# porque el framework sanitiza el HTML. components.html() sí ejecuta scripts
# porque renderiza en un iframe independiente.

import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime


class SessionManager:
    """
    Gestor de sesión que mantiene la sesión activa y persistente.
    Previene cierres automáticos por timeout de Railway/Streamlit/proxies.
    """

    SESSION_TIMEOUT_HOURS = 12  # 12 horas de sesión activa

    # ── Inicialización ────────────────────────────────────────────────────────

    @staticmethod
    def init_session():
        """
        Inicializa el sistema de gestión de sesión.
        Debe llamarse al inicio de cada rerun de la aplicación.
        """
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = time.time()
        if 'heartbeat_counter' not in st.session_state:
            st.session_state.heartbeat_counter = 0

    # ── Actividad ─────────────────────────────────────────────────────────────

    @staticmethod
    def update_activity():
        """Actualiza el timestamp de última actividad."""
        st.session_state.last_activity = time.time()
        st.session_state.heartbeat_counter = st.session_state.get('heartbeat_counter', 0) + 1

    @staticmethod
    def is_session_expired() -> bool:
        """Verifica si la sesión ha expirado por inactividad."""
        if 'last_activity' not in st.session_state:
            return True
        elapsed_hours = (time.time() - st.session_state.last_activity) / 3600
        return elapsed_hours > SessionManager.SESSION_TIMEOUT_HOURS

    @staticmethod
    def get_session_info() -> dict:
        """Obtiene información sobre la sesión actual."""
        if 'last_activity' not in st.session_state:
            return {'active': False, 'elapsed_time': 0, 'heartbeats': 0}

        elapsed_seconds = time.time() - st.session_state.last_activity
        return {
            'active':          True,
            'elapsed_seconds': elapsed_seconds,
            'elapsed_minutes': elapsed_seconds / 60,
            'elapsed_hours':   elapsed_seconds / 3600,
            'heartbeats':      st.session_state.get('heartbeat_counter', 0),
            'last_activity':   datetime.fromtimestamp(st.session_state.last_activity).strftime('%Y-%m-%d %H:%M:%S')
        }

    # ── Keep-alive ────────────────────────────────────────────────────────────

    @staticmethod
    def check_and_refresh_session():
        """
        Verifica el estado de la sesión y la refresca si es necesario.
        Inyecta un keep-alive WebSocket real para prevenir desconexiones
        por parte de Railway, Nginx, Cloudflare u otros proxies.

        Estrategia de 3 capas:
          1. websocketPingInterval en config.toml  → Streamlit hace ping cada 25 s
          2. JavaScript fetch al health endpoint   → mantiene el proxy vivo
          3. Detección de actividad del usuario    → actualiza last_activity

        IMPORTANTE: Usa components.html() (no st.markdown()) porque los scripts
        en st.markdown() NO se ejecutan — Streamlit los sanitiza. components.html()
        renderiza en un iframe donde los scripts sí se ejecutan correctamente.
        """
        # Actualizar actividad en cada rerun
        SessionManager.update_activity()

        if not st.session_state.get('logged_in', False):
            return

        # Inyectar keep-alive JavaScript usando components.html()
        # Solo se inyecta una vez por sesión de navegador (controlado por window.__logipartveKA)
        # El height=0 hace que el iframe sea invisible
        keep_alive_html = """
        <script>
        (function() {
            // Evitar inicializar múltiples veces en el mismo contexto
            if (window.__logipartveKA) return;
            window.__logipartveKA = true;

            // ── Capa 1: Ping HTTP al servidor cada 20 segundos ──────────────
            // Usa fetch con keepalive para que el proxy no cierre la conexión
            function pingServer() {
                try {
                    // Hacer ping al servidor padre (no al iframe)
                    var targetUrl = window.parent.location.href;
                    window.parent.fetch(targetUrl, {
                        method: 'GET',
                        keepalive: true,
                        cache: 'no-store'
                    }).catch(function() {});
                } catch(e) {
                    // Si no podemos acceder al padre, hacer ping al propio iframe
                    try {
                        fetch(window.location.href, {
                            method: 'GET',
                            keepalive: true,
                            cache: 'no-store'
                        }).catch(function() {});
                    } catch(e2) {}
                }
            }
            setInterval(pingServer, 20000);

            // ── Capa 2: Detectar actividad del usuario ──────────────────────
            // Registrar eventos en el documento padre
            try {
                var parentDoc = window.parent.document;
                var activityEvents = ['mousedown', 'mousemove', 'keypress',
                                      'scroll', 'touchstart', 'click', 'input'];
                activityEvents.forEach(function(evt) {
                    parentDoc.addEventListener(evt, function() {
                        sessionStorage.setItem('lp_lastActivity', Date.now());
                    }, { passive: true, capture: true });
                });
            } catch(e) {}

            // ── Capa 3: Reconexión automática si el WebSocket cae ───────────
            var wsCheckInterval = setInterval(function() {
                try {
                    var stRoot = window.parent.document.querySelector('[data-testid="stApp"]');
                    var offline = stRoot && stRoot.classList.contains('stApp--offline');
                    if (offline) {
                        // Esperar 3 segundos y recargar para reconectar
                        setTimeout(function() {
                            window.parent.location.reload();
                        }, 3000);
                        clearInterval(wsCheckInterval);
                    }
                } catch(e) {}
            }, 10000);

            console.log('[LogiPartVE] Keep-alive iniciado (ping cada 20s)');
        })();
        </script>
        """
        components.html(keep_alive_html, height=0, scrolling=False)

    @staticmethod
    def keep_alive():
        """
        Alias de check_and_refresh_session para compatibilidad.
        """
        SessionManager.check_and_refresh_session()
