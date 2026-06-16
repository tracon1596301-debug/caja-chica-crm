import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
from streamlit_calendar import calendar

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA PROFESIONAL
# ==========================================
st.set_page_config(
    page_title="Sistema Pro Caja Chica | Enterprise",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. CSS PERSONALIZADO - DISEÑO PROFESIONAL CORPORATIVO
# ==========================================
def load_custom_css():
    st.markdown("""
    <style>
    /* Fondo principal profesional */
    .main {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        color: #1e293b;
    }
    
    /* Sidebar profesional */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        border-right: 2px solid #3b82f6;
    }
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] p {
        color: #f1f5f9 !important;
    }
    
    /* Tarjetas de métricas profesionales */
    .metric-card {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 15px rgba(59, 130, 246, 0.3);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: white;
        margin: 8px 0;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #e0e7ff;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    
    /* Botones profesionales */
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    /* Tablas */
    div[data-testid="stDataFrame"] {
        background: white;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    
    /* Títulos profesionales */
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 700;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {
        background: white;
        border: 1px solid #cbd5e1;
        color: #1e293b;
        border-radius: 6px;
    }
    
    /* Calendario container */
    .calendar-container {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* Ocultar detalle del evento del calendario (JSON) */
    [data-testid="stSidebar"] pre {
        display: none !important;
    }
    
    /* Reducir espacios excesivos */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    
    .stAlert {
        margin: 0.5rem 0;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #f1f5f9;
        border-radius: 8px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f8fafc;
        border-radius: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. CONEXIÓN A BASE DE DATOS
# ==========================================
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("caja_chica_pro.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ==========================================
# 4. INICIALIZACIÓN DE BD (CORREGIDA)
# ==========================================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de Configuración
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    
    # Tabla de Centros de Costo (SOLO 2 COLUMNAS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS centros_costo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL
        )
    ''')
    
    # Tabla de Movimientos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('Ingreso', 'Egreso')),
            centro_costo_id INTEGER,
            concepto TEXT NOT NULL,
            tiene_factura INTEGER NOT NULL DEFAULT 0,
            no_factura TEXT,
            solicitante TEXT NOT NULL,
            monto REAL NOT NULL CHECK(monto > 0),
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (centro_costo_id) REFERENCES centros_costo(id)
        )
    ''')
    
    # Datos semilla
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('saldo_inicial', 16550.00)")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('alerta_saldo_minimo', 2000.00)")
    
    # Centros de costo iniciales (SOLO 2 VALORES)
    centros_iniciales = [
        ("10000", "DIRECCIÓN GENERAL"),
        ("12300", "TESORERÍA"),
        ("16100", "SERVICIOS GENERALES"),
        ("16210", "RECEPCIÓN"),
        ("18000", "SISTEMAS"),
        ("19000", "COMERCIALIZACIÓN"),
        ("20000", "OPERACIÓN"),
        ("99999", "OTROS")
    ]
    
    for codigo, nombre in centros_iniciales:
        cursor.execute(
            "INSERT OR IGNORE INTO centros_costo (codigo, nombre) VALUES (?, ?)",
            (codigo, nombre)
        )
    
    conn.commit()
    return conn

# ==========================================
# 5. FUNCIONES DE NEGOCIO
# ==========================================
def obtener_saldo(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'saldo_inicial'")
    saldo_inicial = cursor.fetchone()['value']
    
    cursor.execute("""
        SELECT SUM(CASE WHEN tipo='Ingreso' THEN monto ELSE -monto END) as neto 
        FROM movimientos
    """)
    neto = cursor.fetchone()['neto'] or 0.0
    
    return saldo_inicial, saldo_inicial + neto

def obtener_estadisticas(conn):
    cursor = conn.cursor()
    
    cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM movimientos WHERE tipo='Ingreso'")
    total_ingresos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM movimientos WHERE tipo='Egreso'")
    total_egresos = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM movimientos 
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    """)
    movimientos_mes = cursor.fetchone()[0]
    
    return {
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'movimientos_mes': movimientos_mes
    }

# ==========================================
# 6. VISTA: DASHBOARD EJECUTIVO
# ==========================================
def vista_dashboard(conn):
    st.title("📊 Dashboard Ejecutivo")
    
    saldo_inicial, saldo_actual = obtener_saldo(conn)
    stats = obtener_estadisticas(conn)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Saldo Inicial</div>
            <div class="metric-value">${saldo_inicial:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
            <div class="metric-label">Total Ingresos</div>
            <div class="metric-value">${stats['total_ingresos']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);">
            <div class="metric-label">Total Egresos</div>
            <div class="metric-value">${stats['total_egresos']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        color = "#10b981" if saldo_actual >= 0 else "#ef4444"
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, {color} 0%, {color} 100%);">
            <div class="metric-label">Saldo Actual</div>
            <div class="metric-value">${saldo_actual:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("📈 Distribución de Gastos por Centro de Costo")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cc.nombre as centro, SUM(m.monto) as total 
            FROM movimientos m 
            JOIN centros_costo cc ON m.centro_costo_id = cc.id 
            WHERE m.tipo = 'Egreso' 
            GROUP BY cc.nombre
            ORDER BY total DESC
        """)
        resultados = cursor.fetchall()
        
        if resultados:
            df_gastos = pd.DataFrame(resultados, columns=['centro', 'total'])
            fig_pie = px.pie(df_gastos, values='total', names='centro', 
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Set3)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#1e293b'),
                height=350
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sin datos de egresos para mostrar.")

    with col_g2:
        st.subheader("📅 Flujo de Caja - Últimos 30 Días")
        cursor.execute("""
            SELECT fecha, tipo, SUM(monto) as total 
            FROM movimientos 
            WHERE fecha >= date('now', '-30 days')
            GROUP BY fecha, tipo 
            ORDER BY fecha
        """)
        resultados_flujo = cursor.fetchall()
        
        if resultados_flujo:
            df_flujo = pd.DataFrame(resultados_flujo, columns=['fecha', 'tipo', 'total'])
            df_flujo_pivot = df_flujo.pivot(index='fecha', columns='tipo', values='total').fillna(0)
            
            fig_bar = go.Figure()
            if 'Ingreso' in df_flujo_pivot.columns:
                fig_bar.add_trace(go.Bar(
                    x=df_flujo_pivot.index, 
                    y=df_flujo_pivot['Ingreso'], 
                    name='Ingresos', 
                    marker_color='#10b981'
                ))
            if 'Egreso' in df_flujo_pivot.columns:
                fig_bar.add_trace(go.Bar(
                    x=df_flujo_pivot.index, 
                    y=df_flujo_pivot['Egreso'], 
                    name='Egresos', 
                    marker_color='#ef4444'
                ))
            fig_bar.update_layout(
                barmode='group',
                xaxis_title="Fecha",
                yaxis_title="Monto ($)",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#1e293b'),
                legend=dict(orientation="h", y=1.05),
                height=350
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sin datos de flujo para mostrar.")
    
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    st.subheader("📈 Resumen por Centro de Costo")
    
    cursor.execute('''
        SELECT cc.codigo, cc.nombre, 
               COUNT(m.id) as num_movimientos,
               SUM(CASE WHEN m.tipo='Egreso' THEN m.monto ELSE 0 END) as total_egresos,
               SUM(CASE WHEN m.tipo='Ingreso' THEN m.monto ELSE 0 END) as total_ingresos
        FROM centros_costo cc
        LEFT JOIN movimientos m ON cc.id = m.centro_costo_id
        GROUP BY cc.id, cc.codigo, cc.nombre
        ORDER BY total_egresos DESC
    ''')
    resultados_resumen = cursor.fetchall()
    
    if resultados_resumen:
        df_resumen = pd.DataFrame(resultados_resumen, 
                                  columns=['Código', 'Centro de Costo', 'Movimientos', 
                                         'Total Egresos', 'Total Ingresos'])
        st.dataframe(df_resumen.style.format({
            'Total Egresos': '${:,.2f}',
            'Total Ingresos': '${:,.2f}'
        }), use_container_width=True)

# ==========================================
# 7. VISTA: GESTIÓN DE CENTROS DE COSTO (CRUD)
# ==========================================
def vista_centros_costo(conn):
    st.title("🏢 Gestión de Centros de Costo")
    
    tab_create, tab_list, tab_edit = st.tabs(["➕ Nuevo Centro", "📋 Lista de Centros", "✏️ Editar/Eliminar"])
    
    with tab_create:
        st.subheader("Crear Nuevo Centro de Costo")
        
        col1, col2 = st.columns(2)
        with col1:
            codigo = st.text_input("Código*", placeholder="Ej: 19000")
            nombre = st.text_input("Nombre*", placeholder="Ej: MARKETING")
        with col2:
            descripcion = st.text_area("Descripción (opcional)", placeholder="Descripción del centro de costo")
        
        if st.button("💾 Guardar Centro de Costo", use_container_width=True):
            if not codigo or not nombre:
                st.error("❌ El código y nombre son obligatorios")
            else:
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO centros_costo (codigo, nombre)
                        VALUES (?, ?)
                    ''', (codigo.upper(), nombre.upper()))
                    conn.commit()
                    st.success(f"✅ Centro de costo '{nombre}' creado exitosamente")
                    st.balloons()
                except sqlite3.IntegrityError:
                    st.error(f"❌ Ya existe un centro de costo con el código '{codigo}'")
    
    with tab_list:
        st.subheader("Centros de Costo Registrados")
        
        cursor = conn.cursor()
        cursor.execute("SELECT codigo, nombre FROM centros_costo ORDER BY codigo")
        centros = cursor.fetchall()
        
        if centros:
            df_centros = pd.DataFrame(centros, columns=['Código', 'Nombre'])
            st.dataframe(df_centros, use_container_width=True, hide_index=True)
            st.metric("Total Centros", len(centros))
        else:
            st.info("No hay centros de costo registrados")
    
    with tab_edit:
        st.subheader("Editar o Eliminar Centro de Costo")
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo, nombre FROM centros_costo ORDER BY codigo")
        centros = cursor.fetchall()
        
        if centros:
            opciones = {f"{c['codigo']} - {c['nombre']}": c['id'] for c in centros}
            seleccion = st.selectbox("Seleccionar Centro de Costo", list(opciones.keys()))
            
            if seleccion:
                centro_id = opciones[seleccion]
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🗑️ Eliminar", use_container_width=True, type="secondary"):
                        cursor.execute("SELECT COUNT(*) FROM movimientos WHERE centro_costo_id=?", (centro_id,))
                        count = cursor.fetchone()[0]
                        
                        if count > 0:
                            st.error(f"⚠️ No se puede eliminar. Este centro tiene {count} movimientos asociados.")
                        else:
                            cursor.execute("DELETE FROM centros_costo WHERE id=?", (centro_id,))
                            conn.commit()
                            st.success("✅ Centro de costo eliminado correctamente")
                            st.rerun()
        else:
            st.info("No hay centros de costo para editar")

# ==========================================
# 8. VISTA: REGISTRO DE MOVIMIENTOS
# ==========================================
def vista_registro(conn):
    st.title("📝 Registrar Movimiento")
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, codigo, nombre FROM centros_costo ORDER BY nombre")
    centros = cursor.fetchall()
    opciones_centros = {f"{c['codigo']} - {c['nombre']}": c['id'] for c in centros}
    
    with st.form("form_transaccion", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            fecha = st.date_input("📅 Fecha de Movimiento", date.today())
            tipo = st.radio("Tipo de Movimiento", ["Egreso", "Ingreso"], horizontal=True)
            centro_seleccionado = st.selectbox("Centro de Costo*", list(opciones_centros.keys()))
            solicitante = st.text_input("Solicitante / Responsable*")
        
        with col2:
            concepto = st.text_area("Concepto / Descripción*", height=100)
            tiene_factura = st.checkbox("¿Cuenta con Factura/Comprobante?")
            no_factura = st.text_input("Número de Factura / Comprobante") if tiene_factura else None
            monto = st.number_input("Monto ($)*", min_value=0.01, step=0.01, format="%.2f")
        
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾 Registrar Transacción", type="primary", use_container_width=True)
        
        if submitted:
            if not solicitante.strip():
                st.error("❌ El campo 'Solicitante' es obligatorio.")
            elif not concepto.strip():
                st.error("❌ El campo 'Concepto' es obligatorio.")
            elif tiene_factura and not no_factura.strip():
                st.error("❌ Si marca que tiene factura, debe ingresar el número de comprobante.")
            else:
                datos = {
                    'fecha': fecha, 
                    'tipo': tipo, 
                    'centro_costo_id': opciones_centros[centro_seleccionado],
                    'concepto': concepto,  
                    'tiene_factura': 1 if tiene_factura else 0,
                    'no_factura': no_factura if tiene_factura else None, 
                    'solicitante': solicitante, 
                    'monto': monto
                }
                
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO movimientos (fecha, tipo, centro_costo_id, concepto, 
                                               tiene_factura, no_factura, solicitante, monto)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datos['fecha'], datos['tipo'], datos['centro_costo_id'],
                        datos['concepto'], datos['tiene_factura'], datos['no_factura'],
                        datos['solicitante'], datos['monto']
                    ))
                    conn.commit()
                    st.success(f"✅ Transacción registrada exitosamente por ${monto:,.2f}")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error en base de datos: {str(e)}")

# ==========================================
# 9. VISTA: HISTORIAL Y AUDITORÍA (SIN background_gradient)
# ==========================================
def vista_historial(conn):
    st.title("📜 Historial y Auditoría")
    
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.id, m.fecha, m.tipo, cc.codigo || ' - ' || cc.nombre as centro, 
               m.concepto, m.solicitante, 
               CASE WHEN m.tiene_factura = 1 THEN 'Sí' ELSE 'No' END as tiene_factura,
               m.no_factura, m.monto 
        FROM movimientos m
        LEFT JOIN centros_costo cc ON m.centro_costo_id = cc.id
        ORDER BY m.fecha DESC, m.id DESC
    ''')
    resultados = cursor.fetchall()
    
    if resultados:
        df = pd.DataFrame(resultados, 
                          columns=['ID', 'Fecha', 'Tipo', 'Centro de Costo', 
                                 'Concepto', 'Solicitante', '¿Factura?', 
                                 'No. Factura', 'Monto'])
        
        with st.expander("🔍 Filtros Avanzados", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                tipo_filtro = st.multiselect("Tipo", df['Tipo'].unique(), default=df['Tipo'].unique())
            with col2:
                centro_filtro = st.multiselect("Centro", df['Centro de Costo'].unique(), default=df['Centro de Costo'].unique())
            with col3:
                factura_filtro = st.multiselect("¿Tiene Factura?", df['¿Factura?'].unique(), default=df['¿Factura?'].unique())
        
        df_filtrado = df[
            df['Tipo'].isin(tipo_filtro) & 
            df['Centro de Costo'].isin(centro_filtro) &
            df['¿Factura?'].isin(factura_filtro)
        ]
        
        # MOSTRAR TABLA SIN background_gradient (evita error de matplotlib)
        st.dataframe(
            df_filtrado.style.format({"Monto": "${:,.2f}"}),
            use_container_width=True,
            height=500
        )
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", len(df_filtrado))
        col2.metric("Monto Total", f"${df_filtrado['Monto'].sum():,.2f}")
        col3.metric("Promedio por Movimiento", f"${df_filtrado['Monto'].mean():,.2f}")
        
        csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Exportar Reporte a CSV (Excel)",
            data=csv,
            file_name=f'reporte_caja_chica_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv',
        )
    else:
        st.info("No hay movimientos registrados en el sistema.")

# ==========================================
# 10. VISTA: CALENDARIO (JSON OCULTO)
# ==========================================
def vista_calendario(conn):
    st.title("📅 Calendario de Movimientos")
    st.markdown("Visualiza todos los movimientos de caja chica en el calendario")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.fecha, m.tipo, m.concepto, m.monto, cc.nombre as centro_costo
        FROM movimientos m
        LEFT JOIN centros_costo cc ON m.centro_costo_id = cc.id
        ORDER BY m.fecha
    """)
    movimientos = cursor.fetchall()
    
    calendar_events = []
    for mov in movimientos:
        color = '#10b981' if mov['tipo'] == 'Ingreso' else '#ef4444'
        calendar_events.append({
            'title': f"{mov['monto']:,.2f} {mov['tipo']}: {mov['concepto'][:30]}...",
            'start': f"{mov['fecha']}T09:00:00",
            'end': f"{mov['fecha']}T17:00:00",
            'backgroundColor': color,
            'borderColor': color,
        })
    
    calendar_options = {
        "editable": False,
        "selectable": True,
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay,listMonth",
        },
        "initialView": "dayGridMonth",
        "locale": "es",
        "firstDay": 1,
        "height": "auto",
    }
    
    custom_css = """
        .fc-event-title {
            font-weight: 700;
            font-size: 0.85em;
        }
        .fc-toolbar-title {
            font-size: 1.5rem;
            color: #1e293b;
        }
        .fc-daygrid-event {
            margin: 2px 0;
            border-radius: 4px;
        }
    """
    
    # NO guardar el resultado (oculta el JSON)
    calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css=custom_css,
        key='calendar_caja_chica'
    )
    
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    st.subheader("📊 Resumen de Movimientos")
    
    if movimientos:
        df_mov = pd.DataFrame(movimientos, columns=['fecha', 'tipo', 'concepto', 'monto', 'centro_costo'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Ingresos", f"${df_mov[df_mov['tipo']=='Ingreso']['monto'].sum():,.2f}")
        with col2:
            st.metric("Total Egresos", f"${df_mov[df_mov['tipo']=='Egreso']['monto'].sum():,.2f}")

# ==========================================
# 11. VISTA: CONFIGURACIÓN
# ==========================================
def vista_configuracion(conn):
    st.title("⚙️ Configuración del Sistema")
    
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'saldo_inicial'")
    saldo_actual = cursor.fetchone()['value']
    
    cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
    alerta_actual = cursor.fetchone()['value']
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Ajuste de Saldo Inicial")
        nuevo_saldo = st.number_input("Saldo Inicial ($)", value=float(saldo_actual), step=100.0)
        if st.button("Actualizar Saldo Inicial", type="primary", use_container_width=True):
            cursor.execute("UPDATE config SET value = ? WHERE key = 'saldo_inicial'", (nuevo_saldo,))
            conn.commit()
            st.success(f"✅ Saldo inicial actualizado a ${nuevo_saldo:,.2f}")
            st.rerun()
            
    with col2:
        st.subheader("⚠️ Parámetros de Alerta")
        nueva_alerta = st.number_input("Saldo Mínimo para Alerta ($)", value=float(alerta_actual), step=100.0)
        if st.button("Actualizar Alerta", type="primary", use_container_width=True):
            cursor.execute("UPDATE config SET value = ? WHERE key = 'alerta_saldo_minimo'", (nueva_alerta,))
            conn.commit()
            st.success(f"✅ Alerta actualizada a ${nueva_alerta:,.2f}")
            st.rerun()
    
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    st.subheader("📋 Centros de Costo Registrados")
    cursor.execute("SELECT codigo, nombre FROM centros_costo ORDER BY codigo")
    centros = cursor.fetchall()
    df_centros = pd.DataFrame(centros, columns=['Código', 'Nombre'])
    st.dataframe(df_centros, use_container_width=True)

# ==========================================
# 12. MAIN (AQUÍ ESTABA EL ERROR PRINCIPAL)
# ==========================================
def main():
    load_custom_css()
    conn = init_db()
    
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 15px;'>
            <h2 style='color: #3b82f6; margin: 0;'>💼 CAJA CHICA</h2>
            <p style='color: #94a3b8; margin: 5px 0;'>Sistema Enterprise</p>
        </div>
        <div style='border-top: 1px solid #334155; margin: 15px 0;'></div>
        """, unsafe_allow_html=True)
        
        saldo_inicial, saldo_actual = obtener_saldo(conn)
        
        st.markdown(f"""
        <div class="metric-card" style="margin: 15px 0;">
            <div class="metric-label">Saldo en Caja</div>
            <div class="metric-value" style="font-size: 1.8rem;">${saldo_actual:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        menu = st.radio(
            "Navegación",
            [
                "📊 Dashboard Ejecutivo",
                "🏢 Centros de Costo",
                "📝 Registrar Movimiento",
                "📜 Historial y Auditoría",
                "📅 Calendario de Movimientos",
                "⚙️ Configuración"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("<div style='border-top: 1px solid #334155; margin: 15px 0;'></div>", unsafe_allow_html=True)
        
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
        alerta_min = cursor.fetchone()['value']
        
        if saldo_actual < alerta_min:
            st.error(f"⚠️ **ALERTA**: Saldo bajo (${saldo_actual:,.2f} < ${alerta_min:,.2f})")
    
    # ⚠️ AQUÍ ESTABA EL ERROR: Las comparaciones no coincidían con las opciones del menú
    if menu == "📊 Dashboard Ejecutivo":
        vista_dashboard(conn)
    elif menu == "🏢 Centros de Costo":
        vista_centros_costo(conn)
    elif menu == "📝 Registrar Movimiento":
        vista_registro(conn)
    elif menu == "📜 Historial y Auditoría":
        vista_historial(conn)
    elif menu == "📅 Calendario de Movimientos":
        vista_calendario(conn)
    elif menu == "⚙️ Configuración":
        vista_configuracion(conn)

if __name__ == "__main__":
    main()
