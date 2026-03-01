# app.py
# Aplicación principal LogiPartVE Pro v7.0

import streamlit as st
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="LogiPartVE Pro",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar módulos
from database.db_manager import DBManager
from services.auth_manager import AuthManager
from services.session_manager import SessionManager
from services.cookie_session import restore_session_from_cookie, save_session_cookie, delete_session_cookie
import os
import sys
from datetime import datetime, timedelta
from components.header import show_header
from views.login_view import show_login
from views.admin_panel import show_admin_panel
from views.analyst_panel import render_analyst_panel
from views.diagnostics_view import show_diagnostics

# CSS global responsive
st.markdown("""
    <style>
    .main { padding: 1rem; }

    .footer {
        position: fixed;
        bottom: 0; left: 0;
        width: 100%;
        background-color: #f8f9fa;
        text-align: center;
        padding: 0.8rem;
        color: #6c757d;
        font-size: 0.9rem;
        border-top: 1px solid #dee2e6;
        z-index: 999;
    }

    .block-container { padding-bottom: 4rem !important; }

    /* ── Dashboard cards ── */
    .dash-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        border-left: 5px solid #1f77b4;
        margin-bottom: 0.5rem;
    }
    .dash-card-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1f77b4;
        line-height: 1.1;
    }
    .dash-card-label {
        font-size: 0.85rem;
        color: #6c757d;
        margin-top: 0.3rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .dash-card-green  { border-left-color: #28a745; }
    .dash-card-green .dash-card-value { color: #28a745; }
    .dash-card-orange { border-left-color: #fd7e14; }
    .dash-card-orange .dash-card-value { color: #fd7e14; }
    .dash-card-red    { border-left-color: #dc3545; }
    .dash-card-red .dash-card-value { color: #dc3545; }
    .dash-card-purple { border-left-color: #6f42c1; }
    .dash-card-purple .dash-card-value { color: #6f42c1; }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        .main { padding: 0.5rem; }
        .footer { font-size: 0.75rem; padding: 0.5rem; }
        .dash-card-value { font-size: 1.6rem; }
    }

    .scroll-top {
        position: fixed; bottom: 60px; right: 20px;
        background-color: #1f77b4; color: white;
        border: none; border-radius: 50%;
        width: 50px; height: 50px;
        font-size: 24px; cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        z-index: 1000; display: none;
    }
    .scroll-top:hover { background-color: #155a8a; }
    </style>

    <script>
    window.onscroll = function() {
        var btn = document.querySelector('.scroll-top');
        if (btn) {
            btn.style.display = (document.body.scrollTop > 300 ||
                document.documentElement.scrollTop > 300) ? "block" : "none";
        }
    };
    function scrollToTop() { window.scrollTo({top: 0, behavior: 'smooth'}); }
    </script>
    <button class="scroll-top" onclick="scrollToTop()">↑</button>
""", unsafe_allow_html=True)

# ── Inicializar BD ─────────────────────────────────────────────────────────
DBManager.init_database()


def ensure_admin_user():
    try:
        import bcrypt
        admin_password = "Lamesita.99"
        admin_user = DBManager.get_user_by_username('admin')
        if not admin_user:
            DBManager.create_user('admin', admin_password, 'Administrador', 'admin', None)
        else:
            if not DBManager.verify_user('admin', admin_password):
                DBManager.change_password(admin_user['id'], admin_password)
    except Exception as e:
        print(f"⚠️  Error admin: {e}")


def ensure_default_config():
    try:
        from database.init_default_config import initialize_default_config
        initialize_default_config()
    except Exception as e:
        print(f"⚠️  Error config: {e}")


ensure_admin_user()
ensure_default_config()


# ── MAIN ───────────────────────────────────────────────────────────────────
def main():
    SessionManager.init_session()

    # Migraciones (una sola vez por sesión)
    if 'migrations_executed' not in st.session_state:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from database.migrations.add_quote_numbering import run_migration
            run_migration()
        except Exception as e:
            print(f"Migración numeración: {e}")
        st.session_state.migrations_executed = True

    if 'countries_migration_executed' not in st.session_state:
        try:
            from database.migrations.update_countries_list import run_migration as update_countries
            update_countries()
        except Exception as e:
            print(f"Migración países: {e}")
        st.session_state.countries_migration_executed = True

    if not AuthManager.is_logged_in():
        restore_session_from_cookie()

    if not AuthManager.is_logged_in():
        show_login()
    else:
        show_main_app()

    st.markdown("""
        <div class="footer">
            LogiPartVE Pro v7.0 © 2026 — Todos los derechos reservados
        </div>
    """, unsafe_allow_html=True)


# ── APLICACIÓN PRINCIPAL ───────────────────────────────────────────────────
def show_main_app():
    SessionManager.check_and_refresh_session()
    show_header()

    user   = AuthManager.get_current_user()
    role   = user['role']
    is_adm = (role == 'admin')

    # ── SIDEBAR ───────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        role_icon  = "👑" if is_adm else "👤"
        role_label = "Administrador" if is_adm else "Analista"
        st.markdown(f"### {role_icon} {user['full_name']}")
        st.caption(f"Rol: {role_label}")
        st.markdown("---")
        st.markdown("### 📋 Menú")

        if is_adm:
            menu_options = [
                "🏠 Dashboard",
                "🔧 Panel de Administración",
                "📝 Crear Cotización",
                "📊 Mis Cotizaciones",
                "🔍 Diagnóstico del Sistema",
            ]
            # Admin: inicio = Dashboard
            default_idx = 0
        else:
            menu_options = [
                "📝 Crear Cotización",
                "📊 Mis Cotizaciones",
            ]
            # Analista: inicio = Crear Cotización
            default_idx = 0

        # Mantener la selección en session_state para no resetear en cada rerun
        if 'selected_menu' not in st.session_state:
            st.session_state.selected_menu = menu_options[default_idx]

        # Si el menú guardado ya no está en las opciones actuales (cambio de rol), resetear
        if st.session_state.selected_menu not in menu_options:
            st.session_state.selected_menu = menu_options[default_idx]

        current_idx = menu_options.index(st.session_state.selected_menu)

        selected_menu = st.radio(
            "",
            menu_options,
            index=current_idx,
            label_visibility="collapsed",
            key="sidebar_radio"
        )
        st.session_state.selected_menu = selected_menu

        st.markdown("---")

        def do_logout():
            AuthManager.logout()
            # Limpiar menú guardado al cerrar sesión
            st.session_state.pop('selected_menu', None)

        if st.button("🚪 Cerrar Sesión", use_container_width=True,
                     key="btn_cerrar_sesion", on_click=do_logout):
            st.rerun()

    # ── CONTENIDO PRINCIPAL ───────────────────────────────────────────────
    if selected_menu == "🏠 Dashboard":
        show_admin_dashboard()
    elif selected_menu == "🔧 Panel de Administración":
        show_admin_panel()
    elif selected_menu == "📝 Crear Cotización":
        render_analyst_panel()
    elif selected_menu == "📊 Mis Cotizaciones":
        from views.my_quotes_panel import render_my_quotes_panel
        render_my_quotes_panel()
    elif selected_menu == "🔍 Diagnóstico del Sistema":
        show_diagnostics()


# ── DASHBOARD DEL ADMINISTRADOR ────────────────────────────────────────────
def show_admin_dashboard():
    """Dashboard ejecutivo para el administrador con métricas reales."""

    user = AuthManager.get_current_user()

    # Saludo dinámico según la hora
    hora = datetime.now().hour
    if hora < 12:
        saludo = "Buenos días"
    elif hora < 18:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    st.markdown(f"## {saludo}, {user['full_name']} 👋")
    st.caption(f"Hoy es {datetime.now().strftime('%A %d de %B de %Y')} — LogiPartVE Pro v7.0")
    st.markdown("---")

    # ── Selector de período ────────────────────────────────────────────────
    periodo_col, _, _ = st.columns([2, 2, 2])
    with periodo_col:
        periodo = st.selectbox(
            "📅 Ver métricas del período:",
            options=["Últimos 7 días", "Últimos 30 días",
                     "Últimos 3 meses", "Último año", "Todo el tiempo"],
            index=1,
            key="dash_periodo"
        )

    period_map = {
        "Últimos 7 días":   'week',
        "Últimos 30 días":  'month',
        "Últimos 3 meses":  'quarter',
        "Último año":       'year',
        "Todo el tiempo":   'all',
    }
    period_key = period_map[periodo]

    # Calcular fecha de corte para filtrar cotizaciones recientes
    days_map = {
        'week': 7, 'month': 30, 'quarter': 90, 'year': 365, 'all': 99999
    }
    cutoff = datetime.now() - timedelta(days=days_map[period_key])

    # ── Cargar datos ───────────────────────────────────────────────────────
    with st.spinner("Cargando métricas..."):
        try:
            stats   = DBManager.get_global_statistics(period_key)
            ranking = DBManager.get_analyst_ranking('quote_count', period_key, limit=10)
            recent  = DBManager.get_all_quotes(limit=200)
        except Exception as e:
            st.error(f"❌ Error al cargar métricas: {e}")
            return

    # Filtrar cotizaciones recientes por período
    recent_filtered = []
    for q in recent:
        try:
            if datetime.fromisoformat(str(q.get('created_at', ''))) >= cutoff:
                recent_filtered.append(q)
        except Exception:
            if period_key == 'all':
                recent_filtered.append(q)

    # ── FILA 1: Métricas principales ──────────────────────────────────────
    st.markdown("### 📊 Resumen General")

    total_quotes   = stats.get('total_quotes', 0)
    total_amount   = stats.get('total_amount', 0.0)
    approval_rate  = stats.get('approval_rate', 0.0)
    active_analysts= stats.get('active_analysts', 0)
    by_status      = stats.get('quotes_by_status', {})

    approved_count = by_status.get('approved', 0)
    draft_count    = by_status.get('draft', 0)
    sent_count     = by_status.get('sent', 0)
    rejected_count = by_status.get('rejected', 0)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="dash-card">
            <div class="dash-card-value">{total_quotes}</div>
            <div class="dash-card-label">Total Cotizaciones</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="dash-card dash-card-green">
            <div class="dash-card-value">${total_amount:,.0f}</div>
            <div class="dash-card-label">Monto Total Cotizado (USD)</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        color_rate = "dash-card-green" if approval_rate >= 50 else "dash-card-orange"
        st.markdown(f"""
        <div class="dash-card {color_rate}">
            <div class="dash-card-value">{approval_rate:.1f}%</div>
            <div class="dash-card-label">Tasa de Aprobación</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="dash-card dash-card-purple">
            <div class="dash-card-value">{active_analysts}</div>
            <div class="dash-card-label">Analistas Activos</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── FILA 2: Desglose por estado ────────────────────────────────────────
    st.markdown("### 📋 Estado de las Cotizaciones")

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.markdown(f"""
        <div class="dash-card">
            <div class="dash-card-value">{draft_count}</div>
            <div class="dash-card-label">📝 Borradores</div>
        </div>""", unsafe_allow_html=True)

    with s2:
        st.markdown(f"""
        <div class="dash-card dash-card-orange">
            <div class="dash-card-value">{sent_count}</div>
            <div class="dash-card-label">📤 Enviadas</div>
        </div>""", unsafe_allow_html=True)

    with s3:
        st.markdown(f"""
        <div class="dash-card dash-card-green">
            <div class="dash-card-value">{approved_count}</div>
            <div class="dash-card-label">✅ Aprobadas</div>
        </div>""", unsafe_allow_html=True)

    with s4:
        st.markdown(f"""
        <div class="dash-card dash-card-red">
            <div class="dash-card-value">{rejected_count}</div>
            <div class="dash-card-label">❌ Rechazadas</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── FILA 3: Ranking de analistas + Últimas cotizaciones ───────────────
    col_rank, col_recent = st.columns([1, 2])

    with col_rank:
        st.markdown("### 🏆 Ranking de Analistas")
        st.caption(f"Por número de cotizaciones — {periodo}")

        if ranking:
            import pandas as pd
            df_rank = pd.DataFrame([
                {
                    "Pos.":     f"#{i+1}",
                    "Analista": r['analyst_name'],
                    "Cotiz.":   int(r['metric_value'])
                }
                for i, r in enumerate(ranking)
            ])
            st.dataframe(df_rank, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos para el período seleccionado")

    with col_recent:
        st.markdown("### 🕐 Últimas Cotizaciones")
        st.caption(f"Más recientes — {periodo}")

        if recent_filtered:
            import pandas as pd

            ESTADO_LABELS = {
                'draft':    '📝 Borrador',
                'sent':     '📤 Enviada',
                'approved': '✅ Aprobada',
                'rejected': '❌ Rechazada',
            }

            rows = []
            for q in recent_filtered[:15]:
                try:
                    fecha = datetime.fromisoformat(
                        str(q.get('created_at', ''))
                    ).strftime('%d/%m/%Y')
                except Exception:
                    fecha = '—'

                rows.append({
                    "N° Cotización": q.get('quote_number', 'N/A'),
                    "Cliente":       q.get('client_name', 'N/A'),
                    "Analista":      q.get('analyst_name', 'N/A'),
                    "Total USD":     f"${float(q.get('total_amount', 0) or 0):,.2f}",
                    "Estado":        ESTADO_LABELS.get(q.get('status', 'draft'), '—'),
                    "Fecha":         fecha,
                })

            df_rec = pd.DataFrame(rows)
            st.dataframe(df_rec, use_container_width=True, hide_index=True)
        else:
            st.info("No hay cotizaciones en el período seleccionado")

    st.markdown("---")

    # ── Accesos rápidos ────────────────────────────────────────────────────
    st.markdown("### ⚡ Accesos Rápidos")
    qa1, qa2, qa3, qa4 = st.columns(4)

    with qa1:
        if st.button("📝 Nueva Cotización", use_container_width=True, type="primary"):
            st.session_state.selected_menu = "📝 Crear Cotización"
            st.rerun()

    with qa2:
        if st.button("📊 Ver Mis Cotizaciones", use_container_width=True):
            st.session_state.selected_menu = "📊 Mis Cotizaciones"
            st.rerun()

    with qa3:
        if st.button("🔧 Panel de Administración", use_container_width=True):
            st.session_state.selected_menu = "🔧 Panel de Administración"
            st.rerun()

    with qa4:
        if st.button("🔍 Diagnóstico del Sistema", use_container_width=True):
            st.session_state.selected_menu = "🔍 Diagnóstico del Sistema"
            st.rerun()


if __name__ == "__main__":
    main()
