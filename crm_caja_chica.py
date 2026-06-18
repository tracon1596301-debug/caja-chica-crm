import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
from fpdf import FPDF
from streamlit_calendar import calendar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tempfile

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
# CSS ELEGANTE CORPORATIVO - PALETA SERIA
# ==========================================
st.markdown("""
<style>
    /* Fondo principal elegante */
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    /* Sidebar elegante */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1929 0%, #1e3a5f 100%);
        border-right: 2px solid #D4AF37;
    }
    
    /* Tarjetas elegantes */
    .metric-card {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(212, 175, 55, 0.3);
        margin: 10px 0;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(212, 175, 55, 0.2);
        border-color: rgba(212, 175, 55, 0.6);
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #F5F5F5;
        margin: 10px 0;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #D4AF37;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: 600;
    }
    
    /* Botones elegantes */
    .stButton>button {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: #F5F5F5;
        border: 1px solid rgba(212, 175, 55, 0.4);
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #2c5282 0%, #1e3a5f 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);
    }
    
    /* Inputs elegantes */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        background: rgba(10, 25, 41, 0.6);
        border: 1px solid rgba(212, 175, 55, 0.3);
        color: #F5F5F5;
        border-radius: 6px;
    }
    
    /* Tablas elegantes */
    div[data-testid="stDataFrame"] {
        background: rgba(44, 62, 80, 0.6);
        border-radius: 8px;
        border: 1px solid rgba(212, 175, 55, 0.2);
    }
    
    /* Títulos elegantes */
    h1, h2, h3 {
        color: #D4AF37;
        font-weight: 600;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    /* Texto en general */
    p, span, label, .stMarkdown {
        color: #E0E0E0;
    }
    
    /* Calendario */
    .calendar-container {
        background: rgba(44, 62, 80, 0.6);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(212, 175, 55, 0.2);
    }
    
    /* Alertas elegantes */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid #D4AF37;
    }
    
    /* Tabs elegantes */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(10, 25, 41, 0.4);
        border-radius: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #E0E0E0;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        color: #D4AF37 !important;
        border-bottom: 2px solid #D4AF37 !important;
    }
    
    /* Expander elegante */
    .streamlit-expanderHeader {
        background: rgba(30, 58, 95, 0.4);
        color: #D4AF37;
        border-radius: 6px;
        font-weight: 500;
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')

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

    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('saldo_inicial', 16550.00)")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('alerta_saldo_minimo', 2000.00)")

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
    
    for codigo, nombre, desc in centros:
        cursor.execute(
            "SELECT COUNT(*) FROM centros_costo WHERE codigo = ?",
            (codigo,)
        )
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute(
                "INSERT INTO centros_costo (codigo, nombre, descripcion) VALUES (?, ?, ?)",
                (codigo, nombre, desc)
            )
    
    conn.commit()
    return conn

# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================
def obtener_saldo(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'saldo_inicial'")
    result = cursor.fetchone()
    saldo_inicial = result['value'] if result and result['value'] is not None else 0.0
    cursor.execute("SELECT SUM(CASE WHEN tipo='Ingreso' THEN monto ELSE -monto END) as neto FROM movimientos")
    result = cursor.fetchone()
    neto = result['neto'] if result and result['neto'] is not None else 0.0
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

def actualizar_movimiento(conn, id_movimiento, datos):
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE movimientos 
            SET fecha=?, tipo=?, centro_costo_id=?, concepto=?, tiene_factura=?, 
                no_factura=?, solicitante=?, monto=?
            WHERE id=?
        ''', (
            datos['fecha'], datos['tipo'], datos['centro_costo_id'],
            datos['concepto'], datos['tiene_factura'], datos['no_factura'],
            datos['solicitante'], datos['monto'], id_movimiento
        ))
        conn.commit()
        return True, "Movimiento actualizado exitosamente."
    except Exception as e:
        return False, f"Error al actualizar: {str(e)}"

def eliminar_movimiento(conn, id_movimiento):
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM movimientos WHERE id=?", (id_movimiento,))
        conn.commit()
        return True, "Movimiento eliminado exitosamente."
    except Exception as e:
        return False, f"Error al eliminar: {str(e)}"

# ==========================================
# GENERACIÓN DE PDF PROFESIONAL
# ==========================================
def generar_pdf_dashboard(conn):
    """Genera un PDF profesional del dashboard"""
    cursor = conn.cursor()
    saldo_inicial, saldo_actual = obtener_saldo(conn)
    
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso'")
    result = cursor.fetchone()
    ingresos = result[0] if result and result[0] is not None else 0.0
    
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Egreso'")
    result = cursor.fetchone()
    egresos = result[0] if result and result[0] is not None else 0.0
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Header
    pdf.set_font('Arial', 'B', 20)
    pdf.set_fill_color(30, 60, 114)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, 'REPORTE EJECUTIVO - CAJA CHICA', 0, 1, 'C', 1)
    
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f'Fecha de Generacion: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
    pdf.ln(5)
    
    # Resumen Ejecutivo
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 60, 114)
    pdf.cell(0, 10, 'RESUMEN EJECUTIVO', 0, 1, 'L')
    pdf.set_draw_color(212, 175, 55)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    # KPIs en tabla
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    
    pdf.cell(47.5, 8, 'SALDO INICIAL', 1, 0, 'C', 1)
    pdf.cell(47.5, 8, 'SALDO ACTUAL', 1, 0, 'C', 1)
    pdf.cell(47.5, 8, 'TOTAL INGRESOS', 1, 0, 'C', 1)
    pdf.cell(47.5, 8, 'TOTAL EGRESOS', 1, 1, 'C', 1)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(47.5, 12, f'${saldo_inicial:,.2f}', 1, 0, 'C')
    pdf.cell(47.5, 12, f'${saldo_actual:,.2f}', 1, 0, 'C')
    
    pdf.set_text_color(16, 185, 129)
    pdf.cell(47.5, 12, f'${ingresos:,.2f}', 1, 0, 'C')
    
    pdf.set_text_color(239, 68, 68)
    pdf.cell(47.5, 12, f'${egresos:,.2f}', 1, 1, 'C')
    
    pdf.ln(5)
    
    # Gráfico de Distribución
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 60, 114)
    pdf.cell(0, 10, 'DISTRIBUCION DE GASTOS POR CENTRO DE COSTO', 0, 1, 'L')
    pdf.set_draw_color(212, 175, 55)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    cursor.execute('''
        SELECT cc.nombre, SUM(m.monto) as total 
        FROM movimientos m 
        JOIN centros_costo cc ON m.centro_costo_id = cc.id 
        WHERE m.tipo = 'Egreso' 
        GROUP BY cc.nombre
        ORDER BY total DESC
        LIMIT 10
    ''')
    resultados = cursor.fetchall()
    
    if resultados:
        fig, ax = plt.subplots(figsize=(8, 4))
        nombres = [row['nombre'][:25] for row in resultados]
        totales = [row['total'] for row in resultados]
        
        colors = plt.cm.Set3(range(len(nombres)))
        wedges, texts, autotexts = ax.pie(
            totales, labels=nombres, autopct='%1.1f%%',
            colors=colors, startangle=90, pctdistance=0.85
        )
        
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        ax.add_artist(centre_circle)
        ax.set_title('Distribucion de Gastos', fontsize=12, fontweight='bold', pad=20)
        plt.tight_layout()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            img_path = tmp_file.name
            plt.savefig(img_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        pdf.image(img_path, x=10, w=190)
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    pdf.ln(5)
    
    # Gráfico de Flujo de Caja
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 60, 114)
    pdf.cell(0, 10, 'FLUJO DE CAJA DIARIO', 0, 1, 'L')
    pdf.set_draw_color(212, 175, 55)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    cursor.execute('''
        SELECT fecha, tipo, SUM(monto) as total 
        FROM movimientos 
        GROUP BY fecha, tipo 
        ORDER BY fecha
        LIMIT 30
    ''')
    resultados_flujo = cursor.fetchall()
    
    if resultados_flujo:
        df_flujo = pd.DataFrame(resultados_flujo, columns=['fecha', 'tipo', 'total'])
        
        fig, ax = plt.subplots(figsize=(8, 4))
        fechas = df_flujo['fecha'].unique()
        ingresos_data = [df_flujo[(df_flujo['fecha']==f) & (df_flujo['tipo']=='Ingreso')]['total'].sum() for f in fechas]
        egresos_data = [df_flujo[(df_flujo['fecha']==f) & (df_flujo['tipo']=='Egreso')]['total'].sum() for f in fechas]
        
        x = range(len(fechas))
        width = 0.35
        
        ax.bar([i - width/2 for i in x], ingresos_data, width, label='Ingresos', color='#10b981')
        ax.bar([i + width/2 for i in x], egresos_data, width, label='Egresos', color='#ef4444')
        
        ax.set_xlabel('Fecha', fontsize=10)
        ax.set_ylabel('Monto ($)', fontsize=10)
        ax.set_title('Flujo de Caja Diario', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([str(f)[-5:] for f in fechas], rotation=45, ha='right', fontsize=8)
        ax.legend()
        plt.tight_layout()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            img_path = tmp_file.name
            plt.savefig(img_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        pdf.image(img_path, x=10, w=190)
        
        if os.path.exists(img_path):
            os.remove(img_path)
    
    pdf.add_page()
    
    # Tabla Resumen por Centro de Costo
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 60, 114)
    pdf.cell(0, 10, 'RESUMEN POR CENTRO DE COSTO', 0, 1, 'L')
    pdf.set_draw_color(212, 175, 55)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    cursor.execute('''
        SELECT cc.codigo, cc.nombre, 
               COUNT(m.id) as num_movimientos,
               SUM(CASE WHEN m.tipo='Egreso' THEN m.monto ELSE 0 END) as total_egresos,
               SUM(CASE WHEN m.tipo='Ingreso' THEN m.monto ELSE 0 END) as total_ingresos
        FROM centros_costo cc
        LEFT JOIN movimientos m ON cc.id = m.centro_costo_id
        GROUP BY cc.id, cc.codigo, cc.nombre
        ORDER BY total_egresos DESC
        LIMIT 15
    ''')
    resultados_resumen = cursor.fetchall()
    
    if resultados_resumen:
        col_widths = [22, 60, 22, 43, 43]
        total_width = sum(col_widths)
        x_start = (210 - total_width) / 2
        
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(30, 60, 114)
        pdf.set_text_color(255, 255, 255)
        
        headers = ['Codigo', 'Centro de Costo', 'Movs.', 'Total Egresos', 'Total Ingresos']
        
        pdf.set_x(x_start)
        for header, width in zip(headers, col_widths):
            pdf.cell(width, 8, header, 1, 0, 'C', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(0, 0, 0)
        
        for idx, row in enumerate(resultados_resumen):
            if idx % 2 == 0:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            pdf.set_x(x_start)
            pdf.cell(col_widths[0], 7, str(row['codigo']), 1, 0, 'C', 1)
            pdf.cell(col_widths[1], 7, str(row['nombre'])[:30], 1, 0, 'L', 1)
            pdf.cell(col_widths[2], 7, str(row['num_movimientos']), 1, 0, 'C', 1)
            pdf.cell(col_widths[3], 7, f"${row['total_egresos']:,.2f}", 1, 0, 'R', 1)
            pdf.cell(col_widths[4], 7, f"${row['total_ingresos']:,.2f}", 1, 1, 'R', 1)
    
    pdf.ln(5)
    
    # Últimos Movimientos
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 60, 114)
    pdf.cell(0, 10, 'ULTIMOS 10 MOVIMIENTOS', 0, 1, 'L')
    pdf.set_draw_color(212, 175, 55)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    
    cursor.execute('''
        SELECT m.fecha, m.tipo, cc.nombre, m.concepto, m.monto 
        FROM movimientos m
        LEFT JOIN centros_costo cc ON m.centro_costo_id = cc.id
        ORDER BY m.fecha DESC, m.id DESC
        LIMIT 10
    ''')
    movimientos = cursor.fetchall()
    
    if movimientos:
        col_widths = [25, 20, 45, 65, 35]
        total_width = sum(col_widths)
        x_start = (210 - total_width) / 2
        
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(30, 60, 114)
        pdf.set_text_color(255, 255, 255)
        
        headers = ['Fecha', 'Tipo', 'Centro', 'Concepto', 'Monto']
        
        pdf.set_x(x_start)
        for header, width in zip(headers, col_widths):
            pdf.cell(width, 8, header, 1, 0, 'C', 1)
        pdf.ln()
        
        pdf.set_font('Arial', '', 8)
        
        for idx, mov in enumerate(movimientos):
            if idx % 2 == 0:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            pdf.set_x(x_start)
            pdf.set_text_color(0, 0, 0)
            
            pdf.cell(col_widths[0], 7, str(mov['fecha'])[-5:], 1, 0, 'C', 1)
            
            if mov['tipo'] == 'Ingreso':
                pdf.set_text_color(16, 185, 129)
            else:
                pdf.set_text_color(239, 68, 68)
            
            pdf.cell(col_widths[1], 7, mov['tipo'][:3], 1, 0, 'C', 1)
            pdf.set_text_color(0, 0, 0)
            
            pdf.cell(col_widths[2], 7, str(mov['nombre'])[:25] if mov['nombre'] else 'N/A', 1, 0, 'L', 1)
            pdf.cell(col_widths[3], 7, str(mov['concepto'])[:35], 1, 0, 'L', 1)
            pdf.cell(col_widths[4], 7, f"${mov['monto']:,.2f}", 1, 1, 'R', 1)
    
    # Footer
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, 'Reporte generado automaticamente - Sistema Caja Chica Enterprise', 0, 0, 'C')
    pdf.cell(0, 5, f'Pagina {pdf.page_no()}', 0, 1, 'C')
    
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
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <div style='font-size: 48px;'>💼</div>
            <h2 style='color: #D4AF37; margin: 10px 0;'>CAJA CHICA</h2>
            <p style='color: #B0B0B0; font-size: 12px;'>SISTEMA ENTERPRISE</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        conn = get_db_connection()
        saldo_inicial, saldo_actual = obtener_saldo(conn)
        
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>SALDO EN CAJA</div>
            <div class='metric-value' style='font-size: 1.8rem;'>${saldo_actual:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
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
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; padding: 10px; color: #808080; font-size: 11px;'>
            <p>© 2025 Sistema Caja Chica</p>
            <p>Enterprise v2.0</p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# VISTAS DEL SISTEMA
# ==========================================

def vista_dashboard(conn):
    st.title("📊 Dashboard Ejecutivo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    saldo_inicial, saldo_actual = obtener_saldo(conn)
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso'")
    result = cursor.fetchone()
    ingresos = result[0] if result and result[0] is not None else 0.0
    
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Egreso'")
    result = cursor.fetchone()
    egresos = result[0] if result and result[0] is not None else 0.0
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>SALDO INICIAL</div>
            <div class='metric-value'>${saldo_inicial:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%);'>
            <div class='metric-label'>TOTAL INGRESOS</div>
            <div class='metric-value'>${ingresos:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #641220 0%, #8b1e3f 100%);'>
            <div class='metric-label'>TOTAL EGRESOS</div>
            <div class='metric-value'>${egresos:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        color_bg = "#1a4d2e" if saldo_actual >= 0 else "#641220"
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, {color_bg} 0%, {color_bg}dd 100%);'>
            <div class='metric-label'>SALDO FINAL</div>
            <div class='metric-value'>${saldo_actual:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
    result = cursor.fetchone()
    alerta_min = result['value'] if result and result['value'] is not None else 2000.00
    if saldo_actual < alerta_min:
        st.error(f"⚠️ **ALERTA CRÍTICA**: El saldo actual (${saldo_actual:,.2f}) ha caído por debajo del mínimo configurado (${alerta_min:,.2f}).")
    
    st.markdown("---")
    
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
                                        name='Ingresos', marker_color='#2d6a4f'))
            if 'Egreso' in df_flujo_pivot.columns:
                fig_bar.add_trace(go.Bar(x=df_flujo_pivot.index, y=df_flujo_pivot['Egreso'], 
                                         name='Egresos', marker_color='#8b1e3f'))
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
                
                cursor.execute("SELECT COUNT(*) as count FROM movimientos WHERE centro_costo_id = ?", (centro_data['id'],))
                count = cursor.fetchone()['count']
                
                if count > 0:
                    st.error(f"⛔ No se puede eliminar: **{centro_data['nombre']}** tiene {count} movimientos asociados.")
                else:
                    st.warning(f"⚠️ ¿Está seguro de eliminar el centro: **{centro_data['nombre']}**?\n\nEsta acción no se puede deshacer.")
                    
                    if st.button("🗑️ Confirmar Eliminación", use_container_width=True, type="secondary"):
                        try:
                            cursor.execute("DELETE FROM centros_costo WHERE id = ?", (centro_data['id'],))
                            conn.commit()
                            st.success("✅ Centro eliminado exitosamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        else:
            st.info("No hay centros de costo registrados")
    
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
    
    tab_ver, tab_editar = st.tabs(["👁️ Ver Movimientos", "✏️ Editar/Eliminar Movimientos"])
    
    with tab_ver:
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
            
            if fecha_inicio and fecha_fin:
                df_filtrado['Fecha'] = pd.to_datetime(df_filtrado['Fecha'])
                df_filtrado = df_filtrado[
                    (df_filtrado['Fecha'] >= pd.Timestamp(fecha_inicio)) & 
                    (df_filtrado['Fecha'] <= pd.Timestamp(fecha_fin))
                ]
            
            st.dataframe(
                df_filtrado.style.format({"Monto": "${:,.2f}"}),
                use_container_width=True,
                height=500
            )
            
            col_s1, col_s2, col_s3 = st.columns(3)
            col_s1.metric("📊 Total Registros", len(df_filtrado))
            col_s2.metric("💰 Monto Total", f"${df_filtrado['Monto'].sum():,.2f}")
            col_s3.metric("📈 Promedio", f"${df_filtrado['Monto'].mean():,.2f}")
            
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
    
    with tab_editar:
        st.subheader("✏️ Modificar o Eliminar Movimientos")
        
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.id, m.fecha, m.tipo, m.centro_costo_id, cc.nombre as centro_nombre,
                   m.concepto, m.tiene_factura, m.no_factura, m.solicitante, m.monto
            FROM movimientos m
            LEFT JOIN centros_costo cc ON m.centro_costo_id = cc.id
            ORDER BY m.fecha DESC, m.id DESC
        ''')
        movimientos = cursor.fetchall()
        
        if movimientos:
            opciones = {f"{m['id']} - {m['fecha']} - {m['concepto'][:30]} (${m['monto']:,.2f})": m for m in movimientos}
            movimiento_seleccionado = st.selectbox("Seleccionar Movimiento", list(opciones.keys()))
            
            if movimiento_seleccionado:
                mov_data = opciones[movimiento_seleccionado]
                
                cursor.execute("SELECT id, codigo, nombre FROM centros_costo WHERE activo = 1 ORDER BY codigo")
                centros = cursor.fetchall()
                opciones_centros = {f"{c['codigo']} - {c['nombre']}": c['id'] for c in centros}
                
                centro_actual = None
                for label, id_cc in opciones_centros.items():
                    if id_cc == mov_data['centro_costo_id']:
                        centro_actual = label
                        break
                
                # ==========================================
                # FORMULARIO PARA ACTUALIZAR (SOLO ACTUALIZAR)
                # ==========================================
                st.markdown("### 💾 Actualizar Movimiento")
                with st.form("form_actualizar_movimiento"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nueva_fecha = st.date_input("Fecha", value=mov_data['fecha'])
                        nuevo_tipo = st.radio("Tipo", ["Egreso", "Ingreso"], 
                                            index=0 if mov_data['tipo']=="Egreso" else 1, 
                                            horizontal=True)
                        nuevo_centro = st.selectbox("Centro de Costo", list(opciones_centros.keys()), 
                                                   index=list(opciones_centros.keys()).index(centro_actual) if centro_actual else 0)
                        nuevo_solicitante = st.text_input("Solicitante", value=mov_data['solicitante'])
                    
                    with col2:
                        nuevo_concepto = st.text_area("Concepto", value=mov_data['concepto'], height=80)
                        nueva_factura = st.checkbox("¿Tiene Factura?", value=bool(mov_data['tiene_factura']))
                        nuevo_no_factura = st.text_input("No. Factura", value=mov_data['no_factura'] or "")
                        nuevo_monto = st.number_input("Monto ($)", min_value=0.01, value=float(mov_data['monto']), step=0.01)
                    
                    btn_actualizar = st.form_submit_button("💾 Actualizar Movimiento", type="primary", use_container_width=True)
                    
                    if btn_actualizar:
                        if not nuevo_solicitante.strip():
                            st.error("⛔ El campo 'Solicitante' es obligatorio.")
                        elif not nuevo_concepto.strip():
                            st.error("⛔ El campo 'Concepto' es obligatorio.")
                        elif nueva_factura and not nuevo_no_factura.strip():
                            st.error("⛔ Si marca que tiene factura, debe ingresar el número de comprobante.")
                        else:
                            datos = {
                                'fecha': nueva_fecha,
                                'tipo': nuevo_tipo,
                                'centro_costo_id': opciones_centros[nuevo_centro],
                                'concepto': nuevo_concepto,
                                'tiene_factura': 1 if nueva_factura else 0,
                                'no_factura': nuevo_no_factura if nueva_factura else None,
                                'solicitante': nuevo_solicitante,
                                'monto': nuevo_monto
                            }
                            exito, msg = actualizar_movimiento(conn, mov_data['id'], datos)
                            if exito:
                                st.success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                
                st.markdown("---")
                
                # ==========================================
                # SECCIÓN PARA ELIMINAR (FUERA DEL FORM)
                # ==========================================
                st.markdown("### 🗑️ Eliminar Movimiento")
                st.warning(f"⚠️ **¿Está seguro de eliminar este movimiento?**\n\n- **ID:** {mov_data['id']}\n- **Fecha:** {mov_data['fecha']}\n- **Tipo:** {mov_data['tipo']}\n- **Concepto:** {mov_data['concepto']}\n- **Monto:** ${mov_data['monto']:,.2f}\n\n**Esta acción no se puede deshacer.**")
                
                if st.button("🗑️ CONFIRMAR ELIMINACIÓN", type="secondary", use_container_width=True, key="btn_eliminar_mov"):
                    exito, msg = eliminar_movimiento(conn, mov_data['id'])
                    if exito:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.info("No hay movimientos registrados para editar.")

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
        color = '#2d6a4f' if mov['tipo'] == 'Ingreso' else '#8b1e3f'
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
            background: rgba(44, 62, 80, 0.6);
            border-radius: 10px;
            padding: 10px;
        }
        .fc-event-title {
            font-weight: 700;
            font-size: 0.85em;
        }
        .fc-toolbar-title {
            font-size: 1.5rem;
            color: #D4AF37;
        }
        .fc-daygrid-event {
            margin: 2px 0;
            border-radius: 4px;
        }
        .fc-col-header-cell {
            background: rgba(212, 175, 55, 0.1);
            color: #D4AF37;
        }
        .fc-day-today {
            background: rgba(212, 175, 55, 0.15) !important;
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
    
    st.subheader("📊 Resumen de Movimientos")
    
    if movimientos:
        df_mov = pd.DataFrame(movimientos, columns=['fecha', 'tipo', 'concepto', 'monto', 'centro_costo'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%);'>
                <div class='metric-label'>TOTAL INGRESOS</div>
                <div class='metric-value' style='font-size: 1.5rem;'>${df_mov[df_mov['tipo']=='Ingreso']['monto'].sum():,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, #641220 0%, #8b1e3f 100%);'>
                <div class='metric-label'>TOTAL EGRESOS</div>
                <div class='metric-value' style='font-size: 1.5rem;'>${df_mov[df_mov['tipo']=='Egreso']['monto'].sum():,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            neto = df_mov[df_mov['tipo']=='Ingreso']['monto'].sum() - df_mov[df_mov['tipo']=='Egreso']['monto'].sum()
            color_bg = "#1a4d2e" if neto >= 0 else "#641220"
            st.markdown(f"""
            <div class='metric-card' style='background: linear-gradient(135deg, {color_bg} 0%, {color_bg}dd 100%);'>
                <div class='metric-label'>BALANCE NETO</div>
                <div class='metric-value' style='font-size: 1.5rem;'>${neto:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No hay movimientos registrados para mostrar en el calendario.")

def vista_configuracion(conn):
    st.title("⚙️ Configuración del Sistema")
    
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'saldo_inicial'")
    result = cursor.fetchone()
    saldo_actual = result['value'] if result and result['value'] is not None else 16550.00
    
    cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
    result = cursor.fetchone()
    alerta_actual = result['value'] if result and result['value'] is not None else 2000.00
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Ajuste de Saldo Inicial")
        nuevo_saldo = st.number_input("Saldo Inicial ($)", value=float(saldo_actual), step=100.0)
        if st.button("Actualizar Saldo Inicial", type="primary", use_container_width=True):
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('saldo_inicial', ?)", (nuevo_saldo,))
            conn.commit()
            st.success(f"✅ Saldo inicial actualizado a ${nuevo_saldo:,.2f}")
            st.rerun()
            
    with col2:
        st.subheader("⚠️ Parámetros de Alerta")
        nueva_alerta = st.number_input("Saldo Mínimo para Alerta ($)", value=float(alerta_actual), step=100.0)
        if st.button("Actualizar Alerta", type="primary", use_container_width=True):
            cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('alerta_saldo_minimo', ?)", (nueva_alerta,))
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
            <h3 style='color: #D4AF37; margin-top: 0;'>📊 Dashboard Ejecutivo</h3>
            <p style='color: #E0E0E0;'>Reporte completo con:</p>
            <ul style='color: #E0E0E0;'>
                <li>Resumen ejecutivo con KPIs</li>
                <li>Gráfico de distribución de gastos</li>
                <li>Flujo de caja diario</li>
                <li>Tabla resumen por centro de costo</li>
                <li>Últimos movimientos registrados</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📥 Generar Dashboard PDF", use_container_width=True, type="primary"):
            try:
                with st.spinner("Generando reporte PDF..."):
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
                import traceback
                st.code(traceback.format_exc())
    
    with col2:
        st.markdown("""
        <div class='metric-card' style='background: linear-gradient(135deg, #1a4d2e 0%, #2d6a4f 100%);'>
            <h3 style='color: #D4AF37; margin-top: 0;'>📈 Reporte de Movimientos</h3>
            <p style='color: #E0E0E0;'>Exporta todos los movimientos a CSV para análisis detallado.</p>
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
    if 'page' not in st.session_state:
        st.session_state['page'] = 'dashboard'
    
    conn = init_db()
    
    sidebar_mejorado()
    
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
