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
            // Evitar inicializar múltiples veces en el mismo contexto de ventana
            if (window.__logipartveKA) return;
            window.__logipartveKA = true;

            // ── Capa 1: Ping HTTP al servidor cada 5 segundos ──────────────
            // Reducido de 10s a 5s para mayor robustez contra proxies agresivos.
            // Usa fetch con keepalive para que Railway/Nginx no cierren la conexión.
            function pingServer() {
                try {
                    var targetUrl = window.parent.location.href;
                    window.parent.fetch(targetUrl, {
                        method: 'GET',
                        keepalive: true,
                        cache: 'no-store'
                    }).catch(function() {});
                } catch(e) {
                    try {
                        fetch(window.location.href, {
                            method: 'GET',
                            keepalive: true,
                            cache: 'no-store'
                        }).catch(function() {});
                    } catch(e2) {}
                }
            }
            setInterval(pingServer, 5000);  // Ping cada 5 segundos

            // ── Capa 2: Detectar actividad del usuario ──────────────────────
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

            // ── Capa 3: Reconexión inteligente si el WebSocket cae ──────────
            // MEJORA v3: Elimina el reload() que destruía st.session_state y
            // causaba cierres de sesión. Ahora usa reintentos de reconexión WS
            // sin recargar la página. Si el WS no vuelve, espera indefinidamente
            // en lugar de hacer reload (el token en localStorage garantiza la
            // restauración automática si el usuario recarga manualmente).
            var _offlineSince = null;
            var _reconnectAttempts = 0;
            var MAX_RECONNECT_ATTEMPTS = 5;
            var wsCheckInterval = setInterval(function() {
                try {
                    var stRoot = window.parent.document.querySelector('[data-testid="stApp"]');
                    var offline = stRoot && stRoot.classList.contains('stApp--offline');
                    if (offline) {
                        if (!_offlineSince) {
                            _offlineSince = Date.now();
                            _reconnectAttempts = 0;
                            console.log('[LogiPartVE] WebSocket caído, iniciando reconexión inteligente...');
                        } else if ((Date.now() - _offlineSince) > 5000) {
                            if (_reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                                _reconnectAttempts++;
                                console.log('[LogiPartVE] Intento de reconexión WS #' + _reconnectAttempts);
                                try {
                                    // Método 1: API oficial de Streamlit
                                    if (typeof window.parent.streamlitReconnect === 'function') {
                                        window.parent.streamlitReconnect();
                                    }
                                    // Método 2: Fetch para mantener el proxy vivo
                                    window.parent.fetch(window.parent.location.href, {
                                        method: 'GET', cache: 'no-store', keepalive: true
                                    }).catch(function() {});
                                } catch(e) {
                                    console.log('[LogiPartVE] Error en reconexión: ' + e);
                                }
                                _offlineSince = Date.now(); // Resetear para el próximo intento
                            } else {
                                // Agotados los intentos: NO hacer reload (destruiría sesión)
                                // Reiniciar ciclo de intentos y seguir esperando
                                console.log('[LogiPartVE] Reiniciando ciclo de reconexión...');
                                _offlineSince = Date.now();
                                _reconnectAttempts = 0;
                            }
                        }
                    } else {
                        // Volvió online: resetear contadores
                        if (_offlineSince) {
                            console.log('[LogiPartVE] WebSocket reconectado exitosamente.');
                            _offlineSince = null;
                            _reconnectAttempts = 0;
                        }
                    }
                } catch(e) {}
            }, 2000);  // Verificar cada 2 segundos si hay offline

            console.log('[LogiPartVE] Keep-alive v3 iniciado (ping cada 5s, reconexión sin reload)');
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
