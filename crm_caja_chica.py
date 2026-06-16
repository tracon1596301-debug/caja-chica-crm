import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
from streamlit_calendar import calendar
import numpy as np

# ==========================================
# CONFIGURACIÓN DE PÁGINA PROFESIONAL
# ==========================================
st.set_page_config(
    page_title="Sistema Pro Caja Chica | Enterprise",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CSS PERSONALIZADO - DISEÑO FUTURISTA
# ==========================================
def load_custom_css():
    st.markdown("""
    <style>
    /* Fondo principal con gradiente */
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
    }
    
    /* Tarjetas de métricas */
    .metric-card {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 40px rgba(59, 130, 246, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 50px rgba(59, 130, 246, 0.4);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: white;
        margin: 10px 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #cbd5e1;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Sidebar mejorado */
    .css-1d391kg {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Botones personalizados */
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
    }
    
    /* Tablas mejoradas */
    div[data-testid="stDataFrame"] {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #f1f5f9;
        font-weight: 700;
    }
    
    /* Alertas personalizadas */
    .alert-success {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 16px;
        border-radius: 12px;
        margin: 16px 0;
        border-left: 4px solid #34d399;
    }
    
    .alert-error {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 16px;
        border-radius: 12px;
        margin: 16px 0;
        border-left: 4px solid #f87171;
    }
    
    /* Contenedores */
    .css-1r6slb0 {
        padding: 2rem;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(59, 130, 246, 0.3);
        color: #e2e8f0;
        border-radius: 8px;
    }
    
    /* Calendario */
    .calendar-container {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# CONEXIÓN A BASE DE DATOS
# ==========================================
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("caja_chica_pro.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# ==========================================
# INICIALIZACIÓN DE BD
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
    
    # Tabla de Centros de Costo
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS centros_costo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            activo INTEGER DEFAULT 1,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    # Centros de costo iniciales
    centros_iniciales = [
        ("10000", "DIRECCIÓN GENERAL", "Área de dirección y gerencia"),
        ("12300", "TESORERÍA", "Departamento de tesorería"),
        ("16100", "SERVICIOS GENERALES", "Servicios generales y mantenimiento"),
        ("16210", "RECEPCIÓN", "Recepción y atención"),
        ("18000", "SISTEMAS", "Departamento de TI y sistemas"),
    ]
    
    for codigo, nombre, desc in centros_iniciales:
        cursor.execute('''
            INSERT OR IGNORE INTO centros_costo (codigo, nombre, descripcion) 
            VALUES (?, ?, ?)
        ''', (codigo, nombre, desc))
    
    conn.commit()
    return conn

# ==========================================
# FUNCIONES DE NEGOCIO
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
    
    # Total ingresos
    cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM movimientos WHERE tipo='Ingreso'")
    total_ingresos = cursor.fetchone()[0]
    
    # Total egresos
    cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM movimientos WHERE tipo='Egreso'")
    total_egresos = cursor.fetchone()[0]
    
    # Movimientos del mes
    cursor.execute("""
        SELECT COUNT(*) FROM movimientos 
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    """)
    movimientos_mes = cursor.fetchone()[0]
    
    # Centro más gastador
    cursor.execute("""
        SELECT cc.nombre, SUM(m.monto) as total
        FROM movimientos m
        JOIN centros_costo cc ON m.centro_costo_id = cc.id
        WHERE m.tipo = 'Egreso'
        GROUP BY cc.id
        ORDER BY total DESC
        LIMIT 1
    """)
    centro_top = cursor.fetchone()
    
    return {
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'movimientos_mes': movimientos_mes,
        'centro_top': centro_top
    }

# ==========================================
# VISTA: DASHBOARD EJECUTIVO
# ==========================================
def vista_dashboard(conn):
    st.title("📊 Dashboard Ejecutivo")
    
    # Obtener datos
    saldo_inicial, saldo_actual = obtener_saldo(conn)
    stats = obtener_estadisticas(conn)
    
    # Métricas principales en grid
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
    
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    
    # Gráficos en dos columnas
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
                font=dict(color='#e2e8f0'),
                height=400
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
                font=dict(color='#e2e8f0'),
                legend=dict(orientation="h", y=1.05),
                height=400
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sin datos de flujo para mostrar.")
    
    # Calendario de gastos
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    st.subheader("📆 Calendario de Movimientos")
    
    cursor.execute("""
        SELECT fecha, concepto, monto, tipo 
        FROM movimientos 
        ORDER BY fecha DESC
        LIMIT 50
    """)
    movimientos = cursor.fetchall()
    
    if movimientos:
        # Preparar datos para calendario
        calendar_events = []
        for mov in movimientos:
            color = '#10b981' if mov[3] == 'Ingreso' else '#ef4444'
            calendar_events.append({
                'title': f"{mov[1]} - ${mov[2]:,.2f}",
                'start': mov[0],
                'color': color
            })
        
        # Configuración del calendario
        calendar_spec = {
            'display': 'month',
            'editable': False,
            'events': calendar_events
        }
        
        st.markdown("<div class='calendar-container'>", unsafe_allow_html=True)
        calendar_out = calendar(
            spec=calendar_spec,
            key="calendar_gastos"
        )
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# VISTA: GESTIÓN DE CENTROS DE COSTO (CRUD)
# ==========================================
def vista_centros_costo(conn):
    st.title("🏢 Gestión de Centros de Costo")
    
    # Tabs para diferentes operaciones
    tab_create, tab_list, tab_edit = st.tabs(["➕ Nuevo Centro", "📋 Lista de Centros", "✏️ Editar/Eliminar"])
    
    with tab_create:
        st.subheader("Crear Nuevo Centro de Costo")
        
        col1, col2 = st.columns(2)
        with col1:
            codigo = st.text_input("Código*", placeholder="Ej: 19000")
            nombre = st.text_input("Nombre*", placeholder="Ej: MARKETING")
        with col2:
            descripcion = st.text_area("Descripción", placeholder="Descripción del centro de costo")
        
        if st.button("💾 Guardar Centro de Costo", use_container_width=True):
            if not codigo or not nombre:
                st.error("❌ El código y nombre son obligatorios")
            else:
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO centros_costo (codigo, nombre, descripcion, activo)
                        VALUES (?, ?, ?, 1)
                    ''', (codigo.upper(), nombre.upper(), descripcion))
                    conn.commit()
                    st.success(f"✅ Centro de costo '{nombre}' creado exitosamente")
                    st.balloons()
                except sqlite3.IntegrityError:
                    st.error(f"❌ Ya existe un centro de costo con el código '{codigo}'")
    
    with tab_list:
        st.subheader("Centros de Costo Registrados")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            filtro_activo = st.checkbox("Mostrar solo activos", value=True)
        
        cursor = conn.cursor()
        if filtro_activo:
            cursor.execute("SELECT codigo, nombre, descripcion, activo FROM centros_costo WHERE activo=1 ORDER BY codigo")
        else:
            cursor.execute("SELECT codigo, nombre, descripcion, activo FROM centros_costo ORDER BY codigo")
        
        centros = cursor.fetchall()
        
        if centros:
            df_centros = pd.DataFrame(centros, columns=['Código', 'Nombre', 'Descripción', 'Activo'])
            df_centros['Activo'] = df_centros['Activo'].map({1: '✅ Sí', 0: '❌ No'})
            
            st.dataframe(
                df_centros,
                use_container_width=True,
                hide_index=True
            )
            
            # Estadísticas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Centros", len(centros))
            col2.metric("Centros Activos", sum(1 for c in centros if c[3] == 1))
            col3.metric("Centros Inactivos", sum(1 for c in centros if c[3] == 0))
        else:
            st.info("No hay centros de costo registrados")
    
    with tab_edit:
        st.subheader("Editar o Eliminar Centro de Costo")
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo, nombre, descripcion FROM centros_costo ORDER BY codigo")
        centros = cursor.fetchall()
        
        if centros:
            opciones = {f"{c['codigo']} - {c['nombre']}": c['id'] for c in centros}
            seleccion = st.selectbox("Seleccionar Centro de Costo", list(opciones.keys()))
            
            if seleccion:
                centro_id = opciones[seleccion]
                cursor.execute("SELECT * FROM centros_costo WHERE id=?", (centro_id,))
                centro = cursor.fetchone()
                
                col1, col2 = st.columns(2)
                with col1:
                    nuevo_codigo = st.text_input("Código", value=centro['codigo'])
                    nuevo_nombre = st.text_input("Nombre", value=centro['nombre'])
                with col2:
                    nueva_desc = st.text_area("Descripción", value=centro['descripcion'] or "")
                    nuevo_activo = st.checkbox("Activo", value=bool(centro['activo']))
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✏️ Actualizar", use_container_width=True):
                        cursor.execute('''
                            UPDATE centros_costo 
                            SET codigo=?, nombre=?, descripcion=?, activo=?
                            WHERE id=?
                        ''', (nuevo_codigo.upper(), nuevo_nombre.upper(), nueva_desc, 1 if nuevo_activo else 0, centro_id))
                        conn.commit()
                        st.success("✅ Centro de costo actualizado correctamente")
                        st.rerun()
                
                with col_btn2:
                    if st.button("🗑️ Eliminar", use_container_width=True, type="secondary"):
                        # Verificar si tiene movimientos
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
# VISTA: REGISTRO DE MOVIMIENTOS
# ==========================================
def vista_registro(conn):
    st.title("📝 Registrar Movimiento")
    
    # Cargar catálogos
    cursor = conn.cursor()
    cursor.execute("SELECT id, codigo, nombre FROM centros_costo WHERE activo=1 ORDER BY nombre")
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
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾 Registrar Transacción", type="primary", use_container_width=True)
        
        if submitted:
            # Validaciones
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
# VISTA: HISTORIAL Y AUDITORÍA
# ==========================================
def vista_historial(conn):
    st.title("📜 Historial y Auditoría")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id, m.fecha, m.tipo, 
               cc.codigo || ' - ' || cc.nombre as centro, 
               m.concepto, m.solicitante, 
               CASE WHEN m.tiene_factura = 1 THEN 'Sí' ELSE 'No' END as tiene_factura,
               m.no_factura, m.monto 
        FROM movimientos m
        LEFT JOIN centros_costo cc ON m.centro_costo_id = cc.id
        ORDER BY m.fecha DESC, m.id DESC
    """)
    resultados = cursor.fetchall()
    
    if resultados:
        df = pd.DataFrame(resultados, 
                          columns=['ID', 'Fecha', 'Tipo', 'Centro de Costo', 
                                   'Concepto', 'Solicitante', '¿Factura?', 
                                   'No. Factura', 'Monto'])
        
        # Filtros mejorados
        with st.expander("🔍 Filtros Avanzados", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                tipo_filtro = st.multiselect("Tipo", df['Tipo'].unique(), default=df['Tipo'].unique())
            with col2:
                centro_filtro = st.multiselect("Centro", df['Centro de Costo'].unique(), default=df['Centro de Costo'].unique())
            with col3:
                factura_filtro = st.multiselect("¿Tiene Factura?", df['¿Factura?'].unique(), default=df['¿Factura?'].unique())
            with col4:
                fecha_inicio = st.date_input("Desde", value=None)
                fecha_fin = st.date_input("Hasta", value=None)
        
        # Aplicar filtros
        df_filtrado = df[
            df['Tipo'].isin(tipo_filtro) & 
            df['Centro de Costo'].isin(centro_filtro) &
            df['¿Factura?'].isin(factura_filtro)
        ]
        
        if fecha_inicio and fecha_fin:
            df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'])
            df_filtrado = df_filtrado[
                (df_filtrado['Fecha'] >= pd.Timestamp(fecha_inicio)) & 
                (df_filtrado['Fecha'] <= pd.Timestamp(fecha_fin))
            ]
        
        # Mostrar tabla con estilo
        st.dataframe(
            df_filtrado.style.format({"Monto": "${:,.2f}"})
            .background_gradient(subset=['Monto'], cmap='RdYlGn_r'),
            use_container_width=True,
            height=500
        )
        
        # Estadísticas del filtro
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", len(df_filtrado))
        col2.metric("Monto Total", f"${df_filtrado['Monto'].sum():,.2f}")
        col3.metric("Promedio por Movimiento", f"${df_filtrado['Monto'].mean():,.2f}")
        
        # Exportación
        csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Exportar Reporte a CSV",
            data=csv,
            file_name=f'reporte_caja_chica_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv',
            use_container_width=True
        )
    else:
        st.info("No hay movimientos registrados en el sistema.")

# ==========================================
# VISTA: CONFIGURACIÓN
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
    
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    st.subheader("📋 Centros de Costo Registrados")
    cursor.execute("SELECT codigo, nombre, descripcion FROM centros_costo ORDER BY codigo")
    centros = cursor.fetchall()
    df_centros = pd.DataFrame(centros, columns=['Código', 'Nombre', 'Descripción'])
    st.dataframe(df_centros, use_container_width=True)

# ==========================================
# MAIN
# ==========================================
def main():
    load_custom_css()
    conn = init_db()
    
    # Sidebar mejorado
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h2 style='color: #3b82f6; margin: 0;'>💼 CAJA CHICA</h2>
            <p style='color: #94a3b8; margin: 5px 0;'>Sistema Enterprise</p>
        </div>
        <div style='border-top: 1px solid #334155; margin: 20px 0;'></div>
        """, unsafe_allow_html=True)
        
        # Obtener saldos globales
        saldo_inicial, saldo_actual = obtener_saldo(conn)
        
        st.markdown(f"""
        <div class="metric-card" style="margin: 20px 0;">
            <div class="metric-label">Saldo en Caja</div>
            <div class="metric-value" style="font-size: 2rem;">${saldo_actual:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        menu = st.radio(
            "Navegación",
            [
                "📊 Dashboard Ejecutivo",
                "🏢 Centros de Costo",
                "📝 Registrar Movimiento",
                "📜 Historial y Auditoría",
                "⚙️ Configuración"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("<div style='border-top: 1px solid #334155; margin: 20px 0;'></div>", unsafe_allow_html=True)
        
        # Alerta de saldo mínimo
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
        alerta_min = cursor.fetchone()['value']
        
        if saldo_actual < alerta_min:
            st.error(f"⚠️ **ALERTA**: Saldo bajo (${saldo_actual:,.2f} < ${alerta_min:,.2f})")
    
    # Enrutamiento de vistas
    if menu == "📊 Dashboard Ejecutivo":
        vista_dashboard(conn)
    elif menu == "🏢 Centros de Costo":
        vista_centros_costo(conn)
    elif menu == "📝 Registrar Movimiento":
        vista_registro(conn)
    elif menu == "📜 Historial y Auditoría":
        vista_historial(conn)
    elif menu == "⚙️ Configuración":
        vista_configuracion(conn)

if __name__ == "__main__":
    main()
