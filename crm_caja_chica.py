import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# ==========================================
# 1. CONFIGURACIÓN Y OPTIMIZACIÓN DE RECURSOS
# ==========================================
st.set_page_config(
    page_title="Sistema Pro Caja Chica",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Usamos cache_resource para mantener una sola conexión a la BD
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect("caja_chica_pro.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    conn.execute("PRAGMA journal_mode=WAL")  # Optimización de escritura en SQLite
    return conn

# ==========================================
# 2. INICIALIZACIÓN DE BASE DE DATOS
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
    
    # Tabla de Centros de Costo (Catálogo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS centros_costo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL
        )
    ''')
    
    # Tabla de Movimientos (Libro Diario)
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
    
    # Datos semilla (Seed data) basados en tu Excel
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('saldo_inicial', 16550.00)")
    cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('alerta_saldo_minimo', 2000.00)")
    
    # Insertar TODOS los centros de costo del Excel
    centros = [
        ("10000", "DIRECCIÓN GENERAL"),
        ("12300", "TESORERÍA"),
        ("16100", "SERVICIOS GENERALES"),
        ("16210", "RECEPCIÓN"),
        ("18000", "SISTEMAS"),
        ("19000", "COMERCIALIZACIÓN"),
        ("20000", "OPERACIÓN"),
        ("99999", "OTROS")
    ]
    for codigo, nombre in centros:
        cursor.execute("INSERT OR IGNORE INTO centros_costo (codigo, nombre) VALUES (?, ?)", (codigo, nombre))
    
    conn.commit()
    return conn

# ==========================================
# 3. CAPA DE LÓGICA DE NEGOCIO
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

# ==========================================
# 4. INTERFAZ DE USUARIO (UI)
# ==========================================
def main():
    conn = init_db()
    
    # Sidebar de Navegación
    st.sidebar.title("📊 Control Caja Chica")
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", [
        "📊 Dashboard Ejecutivo", 
        "📝 Registrar Movimiento", 
        "📜 Historial y Auditoría", 
        "⚙️ Configuración"
    ])
    
    # Obtener saldos globales para mostrar en el sidebar
    saldo_inicial, saldo_actual = obtener_saldo(conn)
    st.sidebar.metric("💰 Saldo Actual en Caja", f"${saldo_actual:,.2f}")
    
    # Enrutamiento de vistas
    if menu == "📊 Dashboard Ejecutivo":
        vista_dashboard(conn, saldo_inicial, saldo_actual)
    elif menu == "📝 Registrar Movimiento":
        vista_registro(conn)
    elif menu == "📜 Historial y Auditoría":
        vista_historial(conn)
    elif menu == "⚙️ Configuración":
        vista_configuracion(conn)

# --- VISTA 1: DASHBOARD ---
def vista_dashboard(conn, saldo_inicial, saldo_actual):
    st.title("📊 Dashboard Ejecutivo")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Saldo Inicial", f"${saldo_inicial:,.2f}")
    
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Ingreso'")
    ingresos = cursor.fetchone()[0] or 0.0
    col2.metric("Total Ingresos", f"${ingresos:,.2f}", delta=f"${ingresos:,.2f}")
    
    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo='Egreso'")
    egresos = cursor.fetchone()[0] or 0.0
    col3.metric("Total Egresos", f"${egresos:,.2f}", delta=f"-${egresos:,.2f}", delta_color="inverse")
    
    col4.metric("Saldo Final", f"${saldo_actual:,.2f}")
    
    # Alerta de Saldo Mínimo
    cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
    alerta_min = cursor.fetchone()['value']
    if saldo_actual < alerta_min:
        st.error(f"⚠️ **ALERTA CRÍTICA**: El saldo actual (${saldo_actual:,.2f}) ha caído por debajo del mínimo configurado (${alerta_min:,.2f}). Se requiere reposición inmediata.")
    
    st.markdown("---")
    
    # Gráficos
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("Distribución de Gastos por Centro de Costo")
        cursor.execute('''
            SELECT cc.nombre as centro, SUM(m.monto) as total 
            FROM movimientos m 
            JOIN centros_costo cc ON m.centro_costo_id = cc.id 
            WHERE m.tipo = 'Egreso' 
            GROUP BY cc.nombre
        ''')
        resultados = cursor.fetchall()
        
        if resultados:
            # Crear DataFrame con nombres de columna explícitos
            df_gastos = pd.DataFrame(resultados, columns=['centro', 'total'])
            fig_pie = px.pie(df_gastos, values='total', names='centro', hole=0.4, 
                           color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sin datos de egresos para mostrar.")
    
    with col_g2:
        st.subheader("Flujo de Caja Diario")
        cursor.execute('''
            SELECT fecha, tipo, SUM(monto) as total 
            FROM movimientos 
            GROUP BY fecha, tipo 
            ORDER BY fecha
        ''')
        resultados_flujo = cursor.fetchall()
        
        if resultados_flujo:
            # Crear DataFrame con nombres de columna explícitos
            df_flujo = pd.DataFrame(resultados_flujo, columns=['fecha', 'tipo', 'total'])
            df_flujo_pivot = df_flujo.pivot(index='fecha', columns='tipo', values='total').fillna(0)
            
            fig_bar = go.Figure()
            if 'Ingreso' in df_flujo_pivot.columns:
                fig_bar.add_trace(go.Bar(x=df_flujo_pivot.index, y=df_flujo_pivot['Ingreso'], 
                                        name='Ingresos', marker_color='green'))
            if 'Egreso' in df_flujo_pivot.columns:
                fig_bar.add_trace(go.Bar(x=df_flujo_pivot.index, y=df_flujo_pivot['Egreso'], 
                                         name='Egresos', marker_color='red'))
            fig_bar.update_layout(barmode='group', xaxis_title="Fecha", yaxis_title="Monto ($)")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sin datos de flujo para mostrar.")
    
    st.markdown("---")
    st.subheader("📈 Resumen por Centro de Costo")
    
    # Tabla resumen
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

# --- VISTA 2: REGISTRO ---
def vista_registro(conn):
    st.title("📝 Registrar Nuevo Movimiento")
    
    # Cargar catálogos
    cursor = conn.cursor()
    cursor.execute("SELECT id, codigo, nombre FROM centros_costo ORDER BY codigo")
    centros = cursor.fetchall()
    opciones_centros = {f"{c['codigo']} - {c['nombre']}": c['id'] for c in centros}
    
    with st.form("form_transaccion", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha de Movimiento", date.today())
            tipo = st.radio("Tipo de Movimiento", ["Egreso", "Ingreso"], horizontal=True)
            centro_seleccionado = st.selectbox("Centro de Costo", list(opciones_centros.keys()))
            solicitante = st.text_input("Solicitante / Responsable")
        
        with col2:
            concepto = st.text_area("Concepto / Descripción del Gasto")
            tiene_factura = st.checkbox("¿Cuenta con Factura/Comprobante?")
            no_factura = st.text_input("Número de Factura / Comprobante")
            monto = st.number_input("Monto ($)", min_value=0.01, step=0.01, format="%.2f")
            
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾 Registrar Transacción", type="primary", use_container_width=True)
        
        if submitted:
            # Validaciones de Negocio (Estrictas)
            if not solicitante.strip():
                st.error("⛔ El campo 'Solicitante' es obligatorio.")
            elif not concepto.strip():
                st.error("⛔ El campo 'Concepto' es obligatorio.")
            elif tiene_factura and not no_factura.strip():
                st.error("⛔ Si marca que tiene factura, debe ingresar el número de comprobante.")
            else:
                datos = {
                    'fecha': fecha, 'tipo': tipo, 'centro_costo_id': opciones_centros[centro_seleccionado],
                    'concepto': concepto, 'tiene_factura': 1 if tiene_factura else 0,
                    'no_factura': no_factura if tiene_factura else None, 
                    'solicitante': solicitante, 'monto': monto
                }
                exito, msg = registrar_transaccion(conn, datos)
                if exito:
                    st.success(f"✅ {msg}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

# --- VISTA 3: HISTORIAL ---
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
        # Crear DataFrame con nombres de columna explícitos
        df = pd.DataFrame(resultados, 
                          columns=['ID', 'Fecha', 'Tipo', 'Centro de Costo', 
                                 'Concepto', 'Solicitante', '¿Factura?', 
                                 'No. Factura', 'Monto'])
        
        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            tipo_filtro = st.multiselect("Filtrar por Tipo", df['Tipo'].unique(), default=df['Tipo'].unique())
        with col_f2:
            centro_filtro = st.multiselect("Filtrar por Centro", df['Centro de Costo'].unique(), default=df['Centro de Costo'].unique())
        with col_f3:
            factura_filtro = st.multiselect("¿Tiene Factura?", df['¿Factura?'].unique(), default=df['¿Factura?'].unique())
            
        df_filtrado = df[
            df['Tipo'].isin(tipo_filtro) & 
            df['Centro de Costo'].isin(centro_filtro) &
            df['¿Factura?'].isin(factura_filtro)
        ]
        
        # Mostrar tabla
        st.dataframe(
            df_filtrado.style.format({"Monto": "${:,.2f}"}).background_gradient(
                subset=['Monto'], cmap='Reds'
            ),
            use_container_width=True,
            height=500
        )
        
        # Estadísticas del filtro
        st.markdown(f"**Total de registros:** {len(df_filtrado)}")
        st.markdown(f"**Monto total:** ${df_filtrado['Monto'].sum():,.2f}")
        
        # Exportación
        csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Exportar Reporte a CSV (Excel)",
            data=csv,
            file_name=f'reporte_caja_chica_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv',
        )
    else:
        st.info("No hay movimientos registrados en el sistema.")

# --- VISTA 4: CONFIGURACIÓN ---
def vista_configuracion(conn):
    st.title("⚙️ Configuración del Sistema")
    
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = 'saldo_inicial'")
    saldo_actual = cursor.fetchone()['value']
    
    cursor.execute("SELECT value FROM config WHERE key = 'alerta_saldo_minimo'")
    alerta_actual = cursor.fetchone()['value']
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ajuste de Saldo Inicial")
        nuevo_saldo = st.number_input("Saldo Inicial ($)", value=float(saldo_actual), step=100.0)
        if st.button("Actualizar Saldo Inicial", type="primary"):
            cursor.execute("UPDATE config SET value = ? WHERE key = 'saldo_inicial'", (nuevo_saldo,))
            conn.commit()
            st.success(f"✅ Saldo inicial actualizado a ${nuevo_saldo:,.2f}")
            st.rerun()
            
    with col2:
        st.subheader("Parámetros de Alerta")
        nueva_alerta = st.number_input("Saldo Mínimo para Alerta ($)", value=float(alerta_actual), step=100.0)
        if st.button("Actualizar Alerta", type="primary"):
            cursor.execute("UPDATE config SET value = ? WHERE key = 'alerta_saldo_minimo'", (nueva_alerta,))
            conn.commit()
            st.success(f"✅ Alerta actualizada a ${nueva_alerta:,.2f}")
            st.rerun()
    
    st.markdown("---")
    st.subheader("📋 Centros de Costo Registrados")
    cursor.execute("SELECT codigo, nombre FROM centros_costo ORDER BY codigo")
    centros = cursor.fetchall()
    df_centros = pd.DataFrame(centros, columns=['Código', 'Nombre'])
    st.dataframe(df_centros, use_container_width=True)

if __name__ == "__main__":
    main()
