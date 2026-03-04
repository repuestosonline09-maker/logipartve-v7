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
                "🏠 Mi Dashboard",
                "📝 Crear Cotización",
                "📊 Mis Cotizaciones",
            ]
            # Analista: inicio = Mi Dashboard
            default_idx = 0

        # Mantener la selección en session_state para no resetear en cada rerun
        if 'selected_menu' not in st.session_state:
            st.session_state.selected_menu = menu_options[default_idx]

        # Si el menú guardado ya no está en las opciones actuales (cambio de rol), resetear
        if st.session_state.selected_menu not in menu_options:
            st.session_state.selected_menu = menu_options[default_idx]

        current_idx = menu_options.index(st.session_state.selected_menu)

        # Sincronizar el radio con el menú seleccionado programáticamente
        # Solo se asigna si no coincide para evitar conflicto con index=
        if st.session_state.get('sidebar_radio') != menu_options[current_idx]:
            st.session_state['sidebar_radio'] = menu_options[current_idx]

        selected_menu = st.radio(
            "",
            menu_options,
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
    # ── CONTENIDO PRINCIPAL ────────────────────────────────────────────────────
    if selected_menu == "🏠 Dashboard":
        show_admin_dashboard()
    elif selected_menu == "🏠 Mi Dashboard":
        show_analyst_dashboard()
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
    """Dashboard ejecutivo para el administrador con rango de fechas y filtro por analista."""
    import pandas as pd
    from datetime import date

    user = AuthManager.get_current_user()

    # ── Saludo dinámico ────────────────────────────────────────────────────
    hora = datetime.now().hour
    if hora < 12:
        saludo = "Buenos días"
    elif hora < 18:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    DIAS_ES   = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    MESES_ES  = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy = date.today()
    dia_nombre = DIAS_ES[hoy.weekday()]
    mes_nombre = MESES_ES[hoy.month - 1]
    fecha_str  = f"{dia_nombre} {hoy.day} de {mes_nombre} de {hoy.year}"

    st.markdown(f"## {saludo}, {user['full_name']} 👋")
    st.caption(f"Hoy es {fecha_str} — LogiPartVE Pro v7.0")
    st.markdown("---")

    # ── Selector de rango de fechas ────────────────────────────────────────
    primer_dia_mes = hoy.replace(day=1)

    st.markdown("#### 📅 Rango de Fechas")
    col_desde, col_hasta, col_btn = st.columns([2, 2, 1])
    with col_desde:
        fecha_desde = st.date_input(
            "Desde",
            value=st.session_state.get('admin_dash_desde', primer_dia_mes),
            key="admin_dash_desde_input",
            format="DD/MM/YYYY"
        )
    with col_hasta:
        fecha_hasta = st.date_input(
            "Hasta",
            value=st.session_state.get('admin_dash_hasta', hoy),
            key="admin_dash_hasta_input",
            format="DD/MM/YYYY"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        aplicar = st.button("🔍 Aplicar", use_container_width=True, key="admin_dash_aplicar")

    if aplicar:
        st.session_state['admin_dash_desde'] = fecha_desde
        st.session_state['admin_dash_hasta'] = fecha_hasta
    else:
        fecha_desde = st.session_state.get('admin_dash_desde', primer_dia_mes)
        fecha_hasta = st.session_state.get('admin_dash_hasta', hoy)

    # Validar rango
    if fecha_desde > fecha_hasta:
        st.warning("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin.")
        return

    periodo_label = f"{fecha_desde.strftime('%d/%m/%Y')} — {fecha_hasta.strftime('%d/%m/%Y')}"
    st.info(f"📊 Período activo: **{periodo_label}**")
    st.markdown("---")

    fecha_desde_str = fecha_desde.strftime('%Y-%m-%d')
    fecha_hasta_str = fecha_hasta.strftime('%Y-%m-%d')

    # ── Cargar estadísticas globales ───────────────────────────────────────
    with st.spinner("Cargando métricas..."):
        try:
            stats_global = DBManager.get_stats_by_date_range(fecha_desde_str, fecha_hasta_str)
            analistas    = DBManager.get_all_analysts()
            recent       = DBManager.get_all_quotes(limit=500)
        except Exception as e:
            st.error(f"❌ Error al cargar métricas: {e}")
            return

    # Filtrar cotizaciones recientes por rango
    recent_filtered = []
    for q in recent:
        try:
            q_fecha = datetime.fromisoformat(str(q.get('created_at', ''))).date()
            if fecha_desde <= q_fecha <= fecha_hasta:
                recent_filtered.append(q)
        except Exception:
            pass

    total_quotes    = stats_global.get('total_quotes', 0)
    total_amount    = stats_global.get('total_amount', 0.0)
    active_analysts = stats_global.get('active_analysts', 0)
    by_status       = stats_global.get('quotes_by_status', {})
    approved_count  = by_status.get('approved', 0)
    draft_count     = by_status.get('draft', 0)

    # ── BLOQUE GLOBAL ─────────────────────────────────────────────────────
    st.markdown("### 📊 Resumen General")
    c1, c2, c3 = st.columns(3)
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
        st.markdown(f"""
        <div class="dash-card dash-card-purple">
            <div class="dash-card-value">{active_analysts}</div>
            <div class="dash-card-label">Analistas Activos</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 Estado de las Cotizaciones")
    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f"""
        <div class="dash-card">
            <div class="dash-card-value">{draft_count}</div>
            <div class="dash-card-label">📝 Borradores</div>
        </div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""
        <div class="dash-card dash-card-green">
            <div class="dash-card-value">{approved_count}</div>
            <div class="dash-card-label">✅ Aprobadas</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # ── FILTRO POR ANALISTA ────────────────────────────────────────────────
    st.markdown("### 👤 Estadísticas por Analista")

    opciones_analistas = ["— Todos —"] + [a['full_name'] for a in analistas]
    analista_sel = st.selectbox(
        "Seleccionar analista:",
        options=opciones_analistas,
        index=0,
        key="admin_dash_analista"
    )

    if analista_sel != "— Todos —":
        analista_obj = next((a for a in analistas if a['full_name'] == analista_sel), None)
        if analista_obj:
            with st.spinner(f"Cargando datos de {analista_sel}..."):
                stats_a = DBManager.get_stats_by_date_range(
                    fecha_desde_str, fecha_hasta_str,
                    analyst_id=analista_obj['id']
                )

            tq_a  = stats_a.get('total_quotes', 0)
            ta_a  = stats_a.get('total_amount', 0.0)
            bs_a  = stats_a.get('quotes_by_status', {})
            dr_a  = bs_a.get('draft', 0)
            ap_a  = bs_a.get('approved', 0)

            st.markdown(f"#### 📌 {analista_sel}")
            st.caption(f"Período: {periodo_label}")

            a1, a2 = st.columns(2)
            with a1:
                st.markdown(f"""
                <div class="dash-card">
                    <div class="dash-card-value">{tq_a}</div>
                    <div class="dash-card-label">Total Cotizaciones</div>
                </div>""", unsafe_allow_html=True)
            with a2:
                st.markdown(f"""
                <div class="dash-card dash-card-green">
                    <div class="dash-card-value">${ta_a:,.0f}</div>
                    <div class="dash-card-label">Monto Total Cotizado (USD)</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                st.markdown(f"""
                <div class="dash-card">
                    <div class="dash-card-value">{dr_a}</div>
                    <div class="dash-card-label">📝 Borradores</div>
                </div>""", unsafe_allow_html=True)
            with b2:
                st.markdown(f"""
                <div class="dash-card dash-card-green">
                    <div class="dash-card-value">{ap_a}</div>
                    <div class="dash-card-label">✅ Aprobadas</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
    else:
        # Mostrar tabla resumen de todos los analistas
        if analistas:
            filas = []
            for a in analistas:
                s = DBManager.get_stats_by_date_range(fecha_desde_str, fecha_hasta_str, analyst_id=a['id'])
                filas.append({
                    "Analista":         a['full_name'],
                    "Cotizaciones":     s.get('total_quotes', 0),
                    "Monto USD":        f"${s.get('total_amount', 0.0):,.0f}",
                    "Borradores":       s.get('quotes_by_status', {}).get('draft', 0),
                    "Aprobadas":        s.get('quotes_by_status', {}).get('approved', 0),
                })
            df_analistas = pd.DataFrame(filas)
            st.dataframe(df_analistas, use_container_width=True, hide_index=True)
        else:
            st.info("No hay analistas registrados aún.")

    st.markdown("---")

    # ── Últimas cotizaciones del período ───────────────────────────────────
    st.markdown("### 🕐 Últimas Cotizaciones del Período")
    ESTADO_LABELS = {
        'draft':    '📝 Borrador',
        'sent':     '📤 Enviada',
        'approved': '✅ Aprobada',
        'rejected': '❌ Rechazada',
    }
    if recent_filtered:
        rows = []
        for q in recent_filtered[:20]:
            try:
                fecha_q = datetime.fromisoformat(str(q.get('created_at', ''))).strftime('%d/%m/%Y')
            except Exception:
                fecha_q = '—'
            rows.append({
                "N° Cotización": q.get('quote_number', 'N/A'),
                "Cliente":       q.get('client_name', 'N/A'),
                "Analista":      q.get('analyst_name', 'N/A'),
                "Estado":        ESTADO_LABELS.get(q.get('status', 'draft'), '—'),
                "Fecha":         fecha_q,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No hay cotizaciones en el período seleccionado.")

    st.markdown("---")

    # ── Accesos rápidos ────────────────────────────────────────────────────
    st.markdown("### ⚡ Accesos Rápidos")
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("📝 Nueva Cotización", use_container_width=True, type="primary", key="admin_qa1"):
            st.session_state.selected_menu = "📝 Crear Cotización"
            st.rerun()
    with qa2:
        if st.button("📊 Ver Mis Cotizaciones", use_container_width=True, key="admin_qa2"):
            st.session_state.selected_menu = "📊 Mis Cotizaciones"
            st.rerun()
    with qa3:
        if st.button("🔧 Panel de Administración", use_container_width=True, key="admin_qa3"):
            st.session_state.selected_menu = "🔧 Panel de Administración"
            st.rerun()
    with qa4:
        if st.button("🔍 Diagnóstico del Sistema", use_container_width=True, key="admin_qa4"):
            st.session_state.selected_menu = "🔍 Diagnóstico del Sistema"
            st.rerun()


# ── DASHBOARD DEL ANALISTA ──────────────────────────────────────────────
def show_analyst_dashboard():
    """Dashboard personal del analista: solo sus propios datos, aislado del resto."""
    from datetime import date

    user = AuthManager.get_current_user()

    # ── Saludo dinámico ────────────────────────────────────────────────────
    hora = datetime.now().hour
    if hora < 12:
        saludo = "Buenos días"
    elif hora < 18:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    DIAS_ES  = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    MESES_ES = ["enero","febrero","marzo","abril","mayo","junio",
                "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy = date.today()
    dia_nombre = DIAS_ES[hoy.weekday()]
    mes_nombre = MESES_ES[hoy.month - 1]
    fecha_str  = f"{dia_nombre} {hoy.day} de {mes_nombre} de {hoy.year}"

    st.markdown(f"## {saludo}, {user['full_name']} 👋")
    st.caption(f"Hoy es {fecha_str} — LogiPartVE Pro v7.0")
    st.markdown("---")

    # ── Selector de rango de fechas ────────────────────────────────────────
    primer_dia_mes = hoy.replace(day=1)

    st.markdown("#### 📅 Rango de Fechas")
    col_desde, col_hasta, col_btn = st.columns([2, 2, 1])
    with col_desde:
        fecha_desde = st.date_input(
            "Desde",
            value=st.session_state.get('analyst_dash_desde', primer_dia_mes),
            key="analyst_dash_desde_input",
            format="DD/MM/YYYY"
        )
    with col_hasta:
        fecha_hasta = st.date_input(
            "Hasta",
            value=st.session_state.get('analyst_dash_hasta', hoy),
            key="analyst_dash_hasta_input",
            format="DD/MM/YYYY"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        aplicar = st.button("🔍 Aplicar", use_container_width=True, key="analyst_dash_aplicar")

    if aplicar:
        st.session_state['analyst_dash_desde'] = fecha_desde
        st.session_state['analyst_dash_hasta'] = fecha_hasta
    else:
        fecha_desde = st.session_state.get('analyst_dash_desde', primer_dia_mes)
        fecha_hasta = st.session_state.get('analyst_dash_hasta', hoy)

    if fecha_desde > fecha_hasta:
        st.warning("⚠️ La fecha de inicio no puede ser mayor que la fecha de fin.")
        return

    periodo_label = f"{fecha_desde.strftime('%d/%m/%Y')} — {fecha_hasta.strftime('%d/%m/%Y')}"
    st.info(f"📊 Período activo: **{periodo_label}**")
    st.markdown("---")

    fecha_desde_str = fecha_desde.strftime('%Y-%m-%d')
    fecha_hasta_str = fecha_hasta.strftime('%Y-%m-%d')

    # ── Cargar estadísticas del analista (solo sus datos) ───────────────────
    analyst_id = user.get('user_id')
    with st.spinner("Cargando tus métricas..."):
        try:
            stats = DBManager.get_stats_by_date_range(
                fecha_desde_str, fecha_hasta_str,
                analyst_id=analyst_id
            )
        except Exception as e:
            st.error(f"❌ Error al cargar métricas: {e}")
            return

    total_quotes   = stats.get('total_quotes', 0)
    total_amount   = stats.get('total_amount', 0.0)
    by_status      = stats.get('quotes_by_status', {})
    draft_count    = by_status.get('draft', 0)
    approved_count = by_status.get('approved', 0)

    # ── Resumen General ─────────────────────────────────────────────────────
    st.markdown("### 📊 Resumen General")
    c1, c2 = st.columns(2)
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

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Estado de las Cotizaciones ──────────────────────────────────────────
    st.markdown("### 📋 Estado de las Cotizaciones")
    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f"""
        <div class="dash-card">
            <div class="dash-card-value">{draft_count}</div>
            <div class="dash-card-label">📝 Borradores</div>
        </div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""
        <div class="dash-card dash-card-green">
            <div class="dash-card-value">{approved_count}</div>
            <div class="dash-card-label">✅ Aprobadas</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    # ── Últimas cotizaciones del período (solo las del analista) ────────────────
    st.markdown("### 🕐 Mis Últimas Cotizaciones del Período")
    ESTADO_LABELS = {
        'draft':    '📝 Borrador',
        'sent':     '📤 Enviada',
        'approved': '✅ Aprobada',
        'rejected': '❌ Rechazada',
    }
    try:
        import pandas as pd
        mis_quotes = DBManager.get_quotes_by_analyst(analyst_id, limit=500)
        # Filtrar por rango de fechas
        mis_quotes_filtradas = []
        for q in mis_quotes:
            try:
                q_fecha = datetime.fromisoformat(str(q.get('created_at', ''))).date()
                if fecha_desde <= q_fecha <= fecha_hasta:
                    mis_quotes_filtradas.append(q)
            except Exception:
                pass

        if mis_quotes_filtradas:
            rows = []
            for q in mis_quotes_filtradas[:20]:
                try:
                    fecha_q = datetime.fromisoformat(str(q.get('created_at', ''))).strftime('%d/%m/%Y')
                except Exception:
                    fecha_q = '—'
                rows.append({
                    "N° Cotización": q.get('quote_number', 'N/A'),
                    "Cliente":       q.get('client_name', 'N/A'),
                    "Estado":        ESTADO_LABELS.get(q.get('status', 'draft'), '—'),
                    "Fecha":         fecha_q,
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No tienes cotizaciones en el período seleccionado.")
    except Exception as e:
        st.error(f"❌ Error al cargar cotizaciones: {e}")

    st.markdown("---")

    # ── Accesos rápidos ────────────────────────────────────────────────────
    st.markdown("### ⚡ Accesos Rápidos")
    qa1, qa2 = st.columns(2)
    with qa1:
        if st.button("📝 Nueva Cotización", use_container_width=True, type="primary", key="analyst_qa1"):
            st.session_state.selected_menu = "📝 Crear Cotización"
            st.session_state.pop('sidebar_radio', None)
            st.rerun()
    with qa2:
        if st.button("📊 Ver Mis Cotizaciones", use_container_width=True, key="analyst_qa2"):
            st.session_state.selected_menu = "📊 Mis Cotizaciones"
            st.session_state.pop('sidebar_radio', None)
            st.rerun()


if __name__ == "__main__":
    main()
