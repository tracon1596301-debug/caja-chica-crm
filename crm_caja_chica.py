import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
from fpdf import FPDF
from streamlit_calendar import calendar

# ==========================================
# CONFIGURACIÓN DE PÁGINA AVANZADA
# ==========================================
st.set_page_config(
    page_title="Sistema Pro Caja Chica Enterprise",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CSS FUTURISTA PERSONALIZADO
# ==========================================
st.markdown("""
<style>
    /* Fondo principal futurista */
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    /* Sidebar mejorado */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
        border-right: 2px solid #00d4ff;
    }
    
    /* Tarjetas futuristas */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        box-shadow: 0 8px 32px rgba(0, 212, 255, 0.3);
        border: 1px solid rgba(0, 212, 255, 0.3);
        margin: 10px 0;
    }
    
    /* Botones futuristas */
    .stButton>button {
        background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 212, 255, 0.6);
    }
    
    /* Inputs mejorados */
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid #00d4ff;
        color: white;
        border-radius: 8px;
    }
    
    /* Tablas futuristas */
    div[data-testid="stDataFrame"] {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        border: 1px solid rgba(0, 212, 255, 0.3);
    }
    
    /* Alertas mejoradas */
    .stAlert {
        border-radius: 10px;
        border: 1px solid rgba(0, 212, 255, 0.5);
    }
    
    /* Títulos con efecto neón */
    h1, h2, h3 {
        color: #00d4ff;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
    }
    
    /* Texto en general */
    p, span, label, .stMarkdown {
        color: #e0e0e0;
    }
    
    /* Menu items */
    .menu-item {
        padding: 12px 20px;
        margin: 5px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        color: white;
    }
    
    .menu-item:hover {
        background: rgba(0, 212, 255, 0.2);
        transform: translateX(5px);
    }
    
    .menu-item.active {
        background: rgba(0, 212, 255, 0.4);
        border-left: 4px solid #00d4ff;
    }
    
    /* Calendario */
    .calendar-container {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(0, 212, 255, 0.3);
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

    # Datos semilla - Configuración
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('saldo_inicial', 16550.00)")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('alerta_saldo_minimo', 2000.00)")

    # Centros de costo iniciales - Usar INSERT OR IGNORE correctamente
    centros = [
        ("10000", "DIRECCIÓN GENERAL", "Área de dirección y gerencia"),
        ("11000", "DIRECTOR ADJUNTO", "Dirección adjunta"),
        ("12000", "FINANZAS Y CONTABILIDAD", "Departamento financiero"),
        ("12300", "TESORERÍA", "Área de tesorería"),
        ("16100", "SERVICIOS GENERALES", "Servicios generales"),
        ("16210", "RECEPCIÓN", "Recepción"),
        ("18000", "SISTEMAS", "Departamento de TI"),
        ("19000", "COMERCIALIZACIÓN", "Área comercial"),
        ("20000", "OPERACIÓN", "Operaciones"),
        ("99999", "OTROS", "Otros centros de costo")
    ]
    
    # Insertar centros de costo de forma segura
    for codigo, nombre, desc in centros:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO centros_costo (codigo, nombre, descripcion) VALUES (?, ?, ?)",
                (codigo, nombre, desc)
            )
        except sqlite3.IntegrityError:
            # Si ya existe, continuar
            pass
    
    conn.commit()
    return conn

# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================
def obtener_saldo(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'saldo_inicial'")
    saldo_inicial = cursor.fetchone()['value']
    cursor.execute("SELECT SUM(CASE WHEN tipo='Ingreso' THEN monto ELSE -monto END) as neto FROM movimientos")
    neto = cursor.fetchone()['neto'] or 0.0
    return saldo_inicial, saldo_inicial + neto

def registrar_transaccion(conn, datos):
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO movimientos (fecha, tipo, centro_costo_id, concepto, tiene_factura, no_factura, solicitante, monto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['fecha'], datos['tipo'], datos['centro_costo_id'],
            datos['concepto'], datos['tiene_factura'], datos['no_factura'],
            datos['solicitante'], datos['monto']
        ))
        conn.commit()
        return True, "Transacción registrada exitosamente."
    except Exception as e:
        return False, f"Error en base de datos: {str(e)}"

def generar_pdf_dashboard(conn):
    """Genera un PDF profesional del dashboard"""
    cursor = conn.cursor()
    saldo_inicial, saldo_actual = obtener_saldo(conn)
    
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 10, "REPORTE EJECUTIVO - CAJA CHICA", 0, 1, "C")
    pdf.set_font("Arial", "I", 12)
    pdf.cell(0, 10, f"Fecha de Generacion: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")
    pdf.ln(10)
    
    # Métricas principales
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "RESUMEN EJECUTIVO", 0, 1, "L")
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(95, 10, f"Saldo Inicial: ${saldo_inicial:,.2f}", 1, 0, "C")
    pdf.cell(95, 10, f"Saldo Actual: ${saldo_actual:,.2f}", 1, 1, "C")
    
    # Ingresos y Egresos
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso'")
    ingresos = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Egreso'")
    egresos = cursor.fetchone()[0] or 0.0
    
    pdf.cell(95, 10, f"Total Ingresos: ${ingresos:,.2f}", 1, 0, "C")
    pdf.cell(95, 10, f"Total Egresos: ${egresos:,.2f}", 1, 1, "C")
    
    pdf.ln(10)
    
    # Top Centros de Costo
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "TOP 5 CENTROS DE COSTO", 0, 1, "L")
    
    cursor.execute('''
        SELECT cc.nombre, SUM(m.monto) as total 
        FROM movimientos m 
        JOIN centros_costo cc ON m.centro_costo_id = cc.id 
        WHERE m.tipo = 'Egreso' 
        GROUP BY cc.nombre
        ORDER BY total DESC
        LIMIT 5
    ''')
    
    resultados = cursor.fetchall()
    
    pdf.set_font("Arial", "", 11)
    for i, row in enumerate(resultados, 1):
        pdf.cell(10, 8, f"{i}.", 0, 0)
        pdf.cell(100, 8, row['nombre'][:40], 0, 0)
        pdf.cell(80, 8, f"${row['total']:,.2f}", 0, 1, "R")
    
    pdf.ln(10)
    
    # Últimos movimientos
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "ULTIMOS MOVIMIENTOS", 0, 1, "L")
    
    cursor.execute('''
        SELECT m.fecha, m.tipo, cc.nombre, m.concepto, m.monto 
        FROM movimientos m
        LEFT JOIN centros_costo cc ON m.centro_costo_id = cc.id
        ORDER BY m.fecha DESC, m.id DESC
        LIMIT 10
    ''')
    
    movimientos = cursor.fetchall()
    
    pdf.set_font("Arial", "", 9)
    for mov in movimientos:
        fecha = mov['fecha'] if mov['fecha'] else 'N/A'
        tipo = mov['tipo'][:3]
        centro = mov['nombre'][:30] if mov['nombre'] else 'N/A'
        concepto = mov['concepto'][:50] if mov['concepto'] else 'N/A'
        monto = mov['monto']
        
        pdf.cell(25, 6, str(fecha), 0, 0)
        pdf.cell(20, 6, tipo, 0, 0)
        pdf.cell(60, 6, centro, 0, 0)
        pdf.cell(65, 6, concepto, 0, 0)
        pdf.cell(20, 6, f"${monto:,.2f}", 0, 1, "R")
    
    # Footer
    pdf.set_y(-20)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 10, "Reporte generado automaticamente - Sistema Caja Chica Enterprise", 0, 0, "C")
    
    # Guardar PDF en memoria
    nombre_archivo = f"reporte_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin-1')
    
    return nombre_archivo, pdf_bytes

# ==========================================
# SIDEBAR MEJORADO
# ==========================================
def sidebar_mejorado():
    with st.sidebar:
        # Header con logo/branding
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <div style='font-size: 48px;'>💼</div>
            <h2 style='color: #00d4ff; margin: 10px 0;'>CAJA CHICA</h2>
            <p style='color: rgba(255,255,255,0.7); font-size: 12px;'>Sistema Enterprise</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Saldo destacado
        conn = get_db_connection()
        saldo_inicial, saldo_actual = obtener_saldo(conn)
        
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 12px; opacity: 0.8;'>SALDO EN CAJA</div>
            <div style='font-size: 28px; font-weight: bold; margin: 10px 0;'>
                ${saldo_actual:,.2f}
            </div>
            <div style='font-size: 11px; opacity: 0.7;'>
                Inicial: ${saldo_inicial:,.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Menú de navegación mejorado
        menu_items = {
            "📊 Dashboard Ejecutivo": "dashboard",
            "🏢 Centros de Costo": "centros",
            "📝 Registrar Movimiento": "registrar",
            "📜 Historial y Auditoría": "historial",
            "📅 Calendario": "calendario",
            "⚙️ Configuración": "config",
            "📑 Reportes PDF": "reportes"
        }
        
        for label, key in menu_items.items():
            if st.button(label, use_container_width=True, key=f"btn_{key}"):
                st.session_state['page'] = key
                st.rerun()
        
        # Footer del sidebar
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; padding: 10px; color: rgba(255,255,255,0.5); font-size: 11px;'>
            <p>© 2025 Sistema Caja Chica</p>
            <p>Enterprise v2.0</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# VISTAS DEL SISTEMA
# ==========================================

def vista_dashboard(conn):
    st.title("📊 Dashboard Ejecutivo")
    
    # KPIs con diseño mejorado
    col1, col2, col3, col4 = st.columns(4)
    
    saldo_inicial, saldo_actual = obtener_saldo(conn)
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso'")
    ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Egreso'")
    egresos = cursor.fetchone()[0] or 0.0
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 12px;'>SALDO INICIAL</div>
            <div style='font-size: 24px; font-weight: bold;'>${saldo_inicial:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);'>
            <div style='font-size: 12px;'>TOTAL INGRESOS</div>
            <div style='font-size: 24px; font-weight: bold;'>${ingresos:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);'>
            <div style='font-size: 12px;'>TOTAL EGRESOS</div>
            <div style='font-size: 24px; font-weight: bold;'>${egresos:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        color = "#38ef7d" if saldo_actual >= 0 else "#eb3349"
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, {color} 0%, {color}dd 100%);'>
            <div style='font-size: 12px;'>SALDO FINAL</div>
            <div style='font-size: 24px; font-weight: bold;'>${saldo_actual:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Alerta de saldo mínimo
    cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
    alerta_min = cursor.fetchone()['value']
    if saldo_actual < alerta_min:
        st.error(f"⚠️ **ALERTA CRÍTICA**: El saldo actual (${saldo_actual:,.2f}) ha caído por debajo del mínimo configurado (${alerta_min:,.2f}). Se requiere reposición inmediata.")
    
    st.markdown("---")
    
    # Gráficos
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("📊 Distribución de Gastos por Centro de Costo")
        cursor.execute('''
            SELECT cc.nombre as centro, SUM(m.monto) as total 
            FROM movimientos m 
            JOIN centros_costo cc ON m.centro_costo_id = cc.id 
            WHERE m.tipo = 'Egreso' 
            GROUP BY cc.nombre
        ''')
        resultados = cursor.fetchall()
        
        if resultados:
            df_gastos = pd.DataFrame(resultados, columns=['centro', 'total'])
            fig_pie = px.pie(df_gastos, values='total', names='centro', hole=0.4, 
                           color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e0e0e0')
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sin datos de egresos para mostrar.")
    
    with col_g2:
        st.subheader("📈 Flujo de Caja Diario")
        cursor.execute('''
            SELECT fecha, tipo, SUM(monto) as total 
            FROM movimientos 
            GROUP BY fecha, tipo 
            ORDER BY fecha
        ''')
        resultados_flujo = cursor.fetchall()
        
        if resultados_flujo:
            df_flujo = pd.DataFrame(resultados_flujo, columns=['fecha', 'tipo', 'total'])
            df_flujo_pivot = df_flujo.pivot(index='fecha', columns='tipo', values='total').fillna(0)
            
            fig_bar = go.Figure()
            if 'Ingreso' in df_flujo_pivot.columns:
                fig_bar.add_trace(go.Bar(x=df_flujo_pivot.index, y=df_flujo_pivot['Ingreso'], 
                                        name='Ingresos', marker_color='#38ef7d'))
            if 'Egreso' in df_flujo_pivot.columns:
                fig_bar.add_trace(go.Bar(x=df_flujo_pivot.index, y=df_flujo_pivot['Egreso'], 
                                         name='Egresos', marker_color='#eb3349'))
            fig_bar.update_layout(
                barmode='group', 
                xaxis_title="Fecha", 
                yaxis_title="Monto ($)",
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e0e0e0'),
                legend=dict(font=dict(color='#e0e0e0'))
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sin datos de flujo para mostrar.")
    
    st.markdown("---")
    st.subheader("📋 Resumen por Centro de Costo")
    
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

def vista_centros_costo(conn):
    st.title("🏢 Gestión de Centros de Costo")
    
    # Tabs para diferentes acciones
    tab1, tab2, tab3 = st.tabs(["➕ Nuevo Centro", "✏️ Editar Centro", "🗑️ Eliminar Centro"])
    
    cursor = conn.cursor()
    
    with tab1:
        st.subheader("Crear Nuevo Centro de Costo")
        with st.form("form_nuevo_centro"):
            col1, col2 = st.columns(2)
            with col1:
                codigo = st.text_input("Código del Centro")
                nombre = st.text_input("Nombre del Centro")
            with col2:
                descripcion = st.text_area("Descripción")
            
            submitted = st.form_submit_button("💾 Guardar Centro", use_container_width=True)
            
            if submitted:
                if not codigo or not nombre:
                    st.error("⛔ El código y nombre son obligatorios")
                else:
                    try:
                        cursor.execute(
                            "INSERT INTO centros_costo (codigo, nombre, descripcion) VALUES (?, ?, ?)",
                            (codigo.upper(), nombre.upper(), descripcion)
                        )
                        conn.commit()
                        st.success(f"✅ Centro de costo '{nombre}' creado exitosamente")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"⛔ Ya existe un centro de costo con el código '{codigo}'")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    with tab2:
        st.subheader("Editar Centro de Costo")
        
        # Obtener centros existentes
        cursor.execute("SELECT id, codigo, nombre, descripcion FROM centros_costo WHERE activo = 1 ORDER BY codigo")
        centros = cursor.fetchall()
        
        if centros:
            opciones_centros = {f"{c['codigo']} - {c['nombre']}": dict(c) for c in centros}
            centro_seleccionado = st.selectbox("Seleccionar Centro de Costo", list(opciones_centros.keys()))
            
            if centro_seleccionado:
                centro_data = opciones_centros[centro_seleccionado]
                
                with st.form("form_editar_centro"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nuevo_codigo = st.text_input("Código", value=centro_data['codigo'])
                        nuevo_nombre = st.text_input("Nombre", value=centro_data['nombre'])
                    with col2:
                        nueva_descripcion = st.text_area("Descripción", value=centro_data['descripcion'] or "")
                    
                    submitted = st.form_submit_button("💾 Actualizar Centro", use_container_width=True)
                    
                    if submitted:
                        try:
                            cursor.execute('''
                                UPDATE centros_costo 
                                SET codigo=?, nombre=?, descripcion=?
                                WHERE id=?
                            ''', (nuevo_codigo.upper(), nuevo_nombre.upper(), nueva_descripcion, centro_data['id']))
                            conn.commit()
                            st.success("✅ Centro actualizado exitosamente")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(f"⛔ Ya existe un centro con el código '{nuevo_codigo}'")
                        except Exception as e:
                            st.error(f"Error al actualizar: {str(e)}")
        else:
            st.info("No hay centros de costo registrados")
    
    with tab3:
        st.subheader("Eliminar Centro de Costo")
        
        cursor.execute("SELECT id, codigo, nombre, descripcion FROM centros_costo WHERE activo = 1 ORDER BY codigo")
        centros = cursor.fetchall()
        
        if centros:
            opciones_centros = {f"{c['codigo']} - {c['nombre']}": dict(c) for c in centros}
            centro_eliminar = st.selectbox("Seleccionar Centro a Eliminar", list(opciones_centros.keys()), key="select_eliminar")
            
            if centro_eliminar:
                centro_data = opciones_centros[centro_eliminar]
                
                # Verificar si tiene movimientos asociados
                cursor.execute("SELECT COUNT(*) as count FROM movimientos WHERE centro_costo_id = ?", (centro_data['id'],))
                count = cursor.fetchone()['count']
                
                if count > 0:
                    st.error(f"⛔ No se puede eliminar: **{centro_data['nombre']}** tiene {count} movimientos asociados.")
                    st.info("💡 Primero debes eliminar o reasignar los movimientos asociados a este centro.")
                else:
                    st.warning(f"⚠️ ¿Está seguro de eliminar el centro: **{centro_data['nombre']}**?\n\nEsta acción no se puede deshacer.")
                    
                    if st.button("🗑️ Confirmar Eliminación", use_container_width=True, type="primary"):
                        try:
                            cursor.execute("DELETE FROM centros_costo WHERE id = ?", (centro_data['id'],))
                            conn.commit()
                            st.success("✅ Centro eliminado exitosamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.info("No hay centros de costo registrados")
    
    # Mostrar lista de centros
    st.markdown("---")
    st.subheader("📋 Lista de Centros de Costo")
    
    cursor.execute('''
        SELECT cc.codigo, cc.nombre, cc.descripcion, 
               COUNT(m.id) as num_movimientos,
               CASE WHEN cc.activo = 1 THEN 'Activo' ELSE 'Inactivo' END as estado
        FROM centros_costo cc
        LEFT JOIN movimientos m ON cc.id = m.centro_costo_id
        GROUP BY cc.id, cc.codigo, cc.nombre, cc.descripcion, cc.activo
        ORDER BY cc.codigo
    ''')
    
    centros_list = cursor.fetchall()
    
    if centros_list:
        df_centros = pd.DataFrame(centros_list, 
                                  columns=['Código', 'Nombre', 'Descripción', 'Movimientos', 'Estado'])
        st.dataframe(df_centros, use_container_width=True)
    else:
        st.info("No hay centros de costo registrados")

def vista_registro(conn):
    st.title("📝 Registrar Nuevo Movimiento")
    
    # Cargar catálogos
    cursor = conn.cursor()
    cursor.execute("SELECT id, codigo, nombre FROM centros_costo WHERE activo = 1 ORDER BY codigo")
    centros = cursor.fetchall()
    opciones_centros = {f"{c['codigo']} - {c['nombre']}": c['id'] for c in centros}
    
    if not opciones_centros:
        st.error("⛔ No hay centros de costo activos. Primero debes crear al menos uno.")
        return
    
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
            no_factura = st.text_input("Número de Factura / Comprobante")
            monto = st.number_input("Monto ($)*", min_value=0.01, step=0.01, format="%.2f")
            
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾 Registrar Transacción", type="primary", use_container_width=True)
        
        if submitted:
            # Validaciones
            if not solicitante.strip():
                st.error("⛔ El campo 'Solicitante' es obligatorio.")
            elif not concepto.strip():
                st.error("⛔ El campo 'Concepto' es obligatorio.")
            elif tiene_factura and not no_factura.strip():
                st.error("⛔ Si marca que tiene factura, debe ingresar el número de comprobante.")
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
                exito, msg = registrar_transaccion(conn, datos)
                if exito:
                    st.success(f"✅ {msg}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

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
        
        # Filtros
        with st.expander("🔍 Filtros Avanzados", expanded=False):
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                tipo_filtro = st.multiselect("Filtrar por Tipo", df['Tipo'].unique(), default=df['Tipo'].unique())
            with col_f2:
                centro_filtro = st.multiselect("Filtrar por Centro", df['Centro de Costo'].unique(), default=df['Centro de Costo'].unique())
            with col_f3:
                factura_filtro = st.multiselect("¿Tiene Factura?", df['¿Factura?'].unique(), default=df['¿Factura?'].unique())
            
            col_f4, col_f5 = st.columns(2)
            with col_f4:
                fecha_inicio = st.date_input("Desde", value=None)
            with col_f5:
                fecha_fin = st.date_input("Hasta", value=None)
            
        df_filtrado = df[
            df['Tipo'].isin(tipo_filtro) & 
            df['Centro de Costo'].isin(centro_filtro) &
            df['¿Factura?'].isin(factura_filtro)
        ]
        
        # Filtro por fechas
        if fecha_inicio and fecha_fin:
            df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'])
            df_filtrado = df_filtrado[
                (df_filtrado['Fecha'] >= pd.Timestamp(fecha_inicio)) & 
                (df_filtrado['Fecha'] <= pd.Timestamp(fecha_fin))
            ]
        
        # Mostrar tabla SIN background_gradient (evita error de matplotlib)
        st.dataframe(
            df_filtrado.style.format({"Monto": "${:,.2f}"}),
            use_container_width=True,
            height=500
        )
        
        # Estadísticas
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("📊 Total Registros", len(df_filtrado))
        col_s2.metric("💰 Monto Total", f"${df_filtrado['Monto'].sum():,.2f}")
        col_s3.metric("📈 Promedio", f"${df_filtrado['Monto'].mean():,.2f}")
        
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
        color = '#38ef7d' if mov['tipo'] == 'Ingreso' else '#eb3349'
        calendar_events.append({
            'title': f"${mov['monto']:,.2f} {mov['tipo']}",
            'start': str(mov['fecha']),
            'backgroundColor': color,
            'borderColor': color,
            'textColor': '#ffffff',
            'extendedProps': {
                'concepto': mov['concepto'],
                'centro': mov['centro_costo'] or 'N/A',
                'monto': mov['monto'],
                'tipo': mov['tipo']
            }
        })
    
    calendar_options = {
        "editable": False,
        "selectable": True,
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listMonth",
        },
        "initialView": "dayGridMonth",
        "locale": "es",
        "firstDay": 1,
        "height": "auto",
        "themeSystem": "standard",
    }
    
    custom_css = """
        .fc {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 10px;
        }
        .fc-event-title {
            font-weight: 700;
            font-size: 0.85em;
        }
        .fc-toolbar-title {
            font-size: 1.5rem;
            color: #00d4ff;
        }
        .fc-daygrid-event {
            margin: 2px 0;
            border-radius: 4px;
        }
        .fc-col-header-cell {
            background: rgba(0, 212, 255, 0.1);
            color: #00d4ff;
        }
        .fc-day-today {
            background: rgba(0, 212, 255, 0.1) !important;
        }
    """
    
    st.markdown("<div class='calendar-container'>", unsafe_allow_html=True)
    calendar_result = calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css=custom_css,
        key='calendar_caja_chica'
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # Resumen de movimientos
    st.subheader("📊 Resumen de Movimientos")
    
    if movimientos:
        df_mov = pd.DataFrame(movimientos, columns=['fecha', 'tipo', 'concepto', 'monto', 'centro_costo'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);'>
                <div style='font-size: 12px;'>TOTAL INGRESOS</div>
                <div style='font-size: 20px; font-weight: bold;'>${df_mov[df_mov['tipo']=='Ingreso']['monto'].sum():,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);'>
                <div style='font-size: 12px;'>TOTAL EGRESOS</div>
                <div style='font-size: 20px; font-weight: bold;'>${df_mov[df_mov['tipo']=='Egreso']['monto'].sum():,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            neto = df_mov[df_mov['tipo']=='Ingreso']['monto'].sum() - df_mov[df_mov['tipo']=='Egreso']['monto'].sum()
            color = "#38ef7d" if neto >= 0 else "#eb3349"
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, {color} 0%, {color}dd 100%);'>
                <div style='font-size: 12px;'>BALANCE NETO</div>
                <div style='font-size: 20px; font-weight: bold;'>${neto:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No hay movimientos registrados para mostrar en el calendario.")

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
    
    st.markdown("---")
    st.subheader("📋 Centros de Costo Registrados")
    cursor.execute("SELECT codigo, nombre, descripcion FROM centros_costo ORDER BY codigo")
    centros = cursor.fetchall()
    df_centros = pd.DataFrame(centros, columns=['Código', 'Nombre', 'Descripción'])
    st.dataframe(df_centros, use_container_width=True)

def vista_reportes(conn):
    st.title("📑 Reportes Avanzados")
    st.markdown("### Genera reportes profesionales en PDF para presentar a directivos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class='metric-card'>
            <h3 style='color: white; margin-top: 0;'>📊 Dashboard Ejecutivo</h3>
            <p style='color: rgba(255,255,255,0.8);'>Reporte completo con:</p>
            <ul style='color: rgba(255,255,255,0.8);'>
                <li>Resumen ejecutivo</li>
                <li>Top 5 centros de costo</li>
                <li>Últimos movimientos</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📥 Generar Dashboard PDF", use_container_width=True, type="primary"):
            try:
                nombre_archivo, pdf_bytes = generar_pdf_dashboard(conn)
                st.download_button(
                    label="⬇️ Descargar Reporte PDF",
                    data=pdf_bytes,
                    file_name=nombre_archivo,
                    mime='application/pdf',
                    use_container_width=True
                )
                st.success("✅ PDF generado exitosamente. Haz clic en el botón de descarga.")
            except Exception as e:
                st.error(f"Error al generar PDF: {str(e)}")
    
    with col2:
        st.markdown("""
        <div class='metric-card' style='background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);'>
            <h3 style='color: white; margin-top: 0;'>📈 Reporte de Movimientos</h3>
            <p style='color: rgba(255,255,255,0.9);'>Exporta todos los movimientos a CSV para análisis detallado.</p>
        </div>
        """, unsafe_allow_html=True)
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.fecha, m.tipo, cc.nombre as centro, 
                   m.concepto, m.solicitante, m.monto
            FROM movimientos m
            LEFT JOIN centros_costo cc ON m.centro_costo_id = cc.id
            ORDER BY m.fecha DESC
        ''')
        resultados = cursor.fetchall()
        
        if resultados:
            df = pd.DataFrame(resultados, columns=['Fecha', 'Tipo', 'Centro', 'Concepto', 'Solicitante', 'Monto'])
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Descargar CSV Completo",
                data=csv,
                file_name=f'movimientos_completos_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.info("No hay movimientos para exportar.")

# ==========================================
# MAIN
# ==========================================
def main():
    # Inicializar sesión
    if 'page' not in st.session_state:
        st.session_state['page'] = 'dashboard'
    
    conn = init_db()
    
    # Sidebar mejorado
    sidebar_mejorado()
    
    # Navegación
    page = st.session_state.get('page', 'dashboard')
    
    if page == 'dashboard':
        vista_dashboard(conn)
    elif page == 'centros':
        vista_centros_costo(conn)
    elif page == 'registrar':
        vista_registro(conn)
    elif page == 'historial':
        vista_historial(conn)
    elif page == 'calendario':
        vista_calendario(conn)
    elif page == 'config':
        vista_configuracion(conn)
    elif page == 'reportes':
        vista_reportes(conn)

if __name__ == "__main__":
    main()
