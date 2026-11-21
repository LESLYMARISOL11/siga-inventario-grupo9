"""
PROYECTO SIGA - PROGRAMACION 2 - AVANCE 5
Grupo 9 | Tema: Electrodomesticos y Tecnologia
Integrantes: Marisol Gutierrez y Lesly Tobar

Aplicacion web (Streamlit) para el sistema de inventario SIGA.
"""

import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

NOMBRE_BD = "sistema_electrodomesticos_grupo9.db"


# ---------------------------------------------------------------
# 1. BASE DE DATOS: conexion, tablas, datos de prueba y vista
# ---------------------------------------------------------------
@st.cache_resource
def obtener_conexion():
    """Crea UNA sola conexion que Streamlit reutiliza entre ejecuciones."""
    conexion = sqlite3.connect(NOMBRE_BD, check_same_thread=False)
    conexion.execute("PRAGMA foreign_keys = ON")
    crear_base_si_no_existe(conexion)
    return conexion


def crear_base_si_no_existe(conexion):
    """Crea tablas, vista y datos de prueba SOLO si todavia no existen.
    (En Streamlit Cloud los archivos se pierden al reiniciar la app.)"""
    cur = conexion.cursor()

    # Mismas tablas del script (CREATE TABLE IF NOT EXISTS en lugar de DROP)
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT
    );

    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT
    );

    CREATE TABLE IF NOT EXISTS productos (
        id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        categoria TEXT NOT NULL,
        precio_unitario REAL NOT NULL,
        stock_minimo INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS movimientos (
        id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
        cantidad INTEGER NOT NULL CHECK (cantidad > 0),
        fecha TEXT NOT NULL,
        id_proveedor INTEGER,
        id_cliente INTEGER,

        FOREIGN KEY (id_producto) REFERENCES productos(id_producto),
        FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor),
        FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
    );

    -- Vista de inventario (Avance 3): el stock se CALCULA, no se escribe
    CREATE VIEW IF NOT EXISTS vw_inventario AS
    SELECT
        p.id_producto,
        p.nombre,
        p.categoria,
        p.precio_unitario,
        p.stock_minimo,
        COALESCE(
            SUM(
                CASE
                    WHEN m.tipo = 'entrada' THEN m.cantidad
                    WHEN m.tipo = 'salida'  THEN -m.cantidad
                    ELSE 0
                END
            ), 0
        ) AS stock
    FROM productos AS p
    LEFT JOIN movimientos AS m
        ON p.id_producto = m.id_producto
    GROUP BY
        p.id_producto, p.nombre, p.categoria,
        p.precio_unitario, p.stock_minimo;
    """)

    # Datos de prueba: solo si la tabla de productos esta vacia
    hay_productos = cur.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    if hay_productos == 0:
        cur.executemany(
            "INSERT INTO proveedores (nombre, telefono) VALUES (?, ?)",
            [
                ("Distribuciones Electro Valle", "3001234567"),
                ("Tecnologia del Pacifico", "3017654321"),
            ],
        )
        cur.executemany(
            "INSERT INTO clientes (nombre, telefono) VALUES (?, ?)",
            [
                ("Almacenes El Ahorro", "3104567890"),
                ("Comercializadora Cali", "3159876543"),
            ],
        )
        cur.executemany(
            "INSERT INTO productos (nombre, categoria, precio_unitario, stock_minimo) VALUES (?, ?, ?, ?)",
            [
                ("Televisor Smart TV 50 pulgadas", "Electrodomesticos", 1800000, 5),
                ("Nevera No Frost 300 litros", "Electrodomesticos", 2400000, 3),
                ("Computador portatil", "Tecnologia", 2800000, 4),
                ("Celular Smartphone", "Tecnologia", 1200000, 5),
            ],
        )
        # Entradas (compras a proveedores)
        cur.executemany(
            "INSERT INTO movimientos (id_producto, tipo, cantidad, fecha, id_proveedor) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "entrada", 20, "2026-09-01", 1),
                (2, "entrada", 10, "2026-09-01", 1),
                (3, "entrada", 15, "2026-09-02", 2),
                (4, "entrada", 25, "2026-09-02", 2),
            ],
        )
        # Salidas (ventas a clientes)
        cur.executemany(
            "INSERT INTO movimientos (id_producto, tipo, cantidad, fecha, id_cliente) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "salida", 5, "2026-09-10", 1),
                (2, "salida", 2, "2026-09-10", 2),
                (3, "salida", 4, "2026-09-11", 1),
                (4, "salida", 8, "2026-09-11", 2),
            ],
        )
    conexion.commit()


# La conexion y el cursor que usan las funciones del Avance 4
conexion = obtener_conexion()
cursor = conexion.cursor()


# ---------------------------------------------------------------
# 2. FUNCIONES DEL AVANCE 4 (copiadas SIN cambios)
# ---------------------------------------------------------------
def existe_producto(id_producto):
    cursor.execute("SELECT 1 FROM productos WHERE id_producto = ?", (id_producto,))
    return cursor.fetchone() is not None

def existe_proveedor(id_proveedor):
    cursor.execute("SELECT 1 FROM proveedores WHERE id_proveedor = ?", (id_proveedor,))
    return cursor.fetchone() is not None

def existe_cliente(id_cliente):
    cursor.execute("SELECT 1 FROM clientes WHERE id_cliente = ?", (id_cliente,))
    return cursor.fetchone() is not None

def cantidad_valida(cantidad):
    """La cantidad debe ser un numero entero mayor que 0."""
    return isinstance(cantidad, int) and not isinstance(cantidad, bool) and cantidad > 0


def registrar_entrada(id_producto, cantidad, fecha=None, id_proveedor=None):
    fecha = fecha or date.today().isoformat()          # si no dan fecha, usa la de hoy
    # 1. Validar
    if not cantidad_valida(cantidad):
        return False, "La cantidad debe ser un número entero mayor que 0."
    if not existe_producto(id_producto):
        return False, f"El producto {id_producto} no existe."
    if id_proveedor is not None and not existe_proveedor(id_proveedor):
        return False, f"El proveedor {id_proveedor} no existe."
    # 3 y 4. Ejecutar y confirmar (o deshacer)
    try:
        cursor.execute(
            "INSERT INTO movimientos (id_producto, tipo, cantidad, fecha, id_proveedor) "
            "VALUES (?, 'entrada', ?, ?, ?)",
            (id_producto, cantidad, fecha, id_proveedor))
        conexion.commit()
        return True, f"Entrada registrada: {cantidad} unidades del producto {id_producto}."
    except Exception as e:
        conexion.rollback()
        return False, f"Error al guardar: {e}"


def registrar_salida(id_producto, cantidad, fecha=None, id_cliente=None):
    fecha = fecha or date.today().isoformat()
    # 1. Validar
    if not cantidad_valida(cantidad):
        return False, "La cantidad debe ser un número entero mayor que 0."
    if not existe_producto(id_producto):
        return False, f"El producto {id_producto} no existe."
    if id_cliente is not None and not existe_cliente(id_cliente):
        return False, f"El cliente {id_cliente} no existe."
    # 2. Consultar el stock actual en la vista
    cursor.execute("SELECT stock FROM vw_inventario WHERE id_producto = ?", (id_producto,))
    stock = cursor.fetchone()[0]
    if cantidad > stock:
        return False, f"Stock insuficiente: hay {stock} y se piden {cantidad}."
    # 3 y 4. Ejecutar y confirmar (o deshacer)
    try:
        cursor.execute(
            "INSERT INTO movimientos (id_producto, tipo, cantidad, fecha, id_cliente) "
            "VALUES (?, 'salida', ?, ?, ?)",
            (id_producto, cantidad, fecha, id_cliente))
        conexion.commit()
        return True, f"Salida registrada: {cantidad} unidades del producto {id_producto}."
    except Exception as e:
        conexion.rollback()
        return False, f"Error al guardar: {e}"


def consultar_inventario(categoria=None):
    """Devuelve el inventario actual. Si se da una categoria, filtra por ella."""
    if categoria:
        return pd.read_sql_query(
            "SELECT * FROM vw_inventario WHERE categoria = ? ORDER BY nombre",
            conexion, params=(categoria,))
    return pd.read_sql_query("SELECT * FROM vw_inventario ORDER BY nombre", conexion)


def alertas_stock_bajo(minimo=10):
    """Devuelve los productos cuyo stock es menor que el minimo recibido."""
    return pd.read_sql_query(
        "SELECT id_producto, nombre, categoria, stock FROM vw_inventario "
        "WHERE stock < ? ORDER BY stock",
        conexion, params=(minimo,))


# ---------------------------------------------------------------
# 3. INTERFAZ STREAMLIT
# ---------------------------------------------------------------
def mostrar_mensaje_pendiente():
    """Muestra (una sola vez) el resultado del ultimo movimiento registrado."""
    if "mensaje" in st.session_state:
        exito, texto = st.session_state.pop("mensaje")
        if exito:
            st.success(texto)
        else:
            st.error(texto)


def pestana_inicio():
    st.header("SIGA - Sistema de Inventario")
    st.write(
        "Sistema de gestión de inventario para una empresa de "
        "**Electrodomésticos y Tecnología**. Permite registrar entradas y "
        "salidas de productos, consultar el stock actual y ver alertas de "
        "inventario bajo."
    )
    inventario = consultar_inventario()
    productos_bajos = inventario[inventario["stock"] <= inventario["stock_minimo"]]

    col1, col2, col3 = st.columns(3)
    col1.metric("Productos registrados", len(inventario))
    col2.metric("Unidades en stock", int(inventario["stock"].sum()))
    col3.metric("Productos con stock bajo", len(productos_bajos))


def pestana_registrar():
    st.header("Registrar movimiento")
    mostrar_mensaje_pendiente()

    # El producto se escoge por NOMBRE; internamente se usa su id
    productos = pd.read_sql_query(
        "SELECT id_producto, nombre FROM productos ORDER BY nombre", conexion)
    ids_por_nombre = dict(zip(productos["nombre"], productos["id_producto"]))

    with st.form("form_movimiento"):
        nombre = st.selectbox("Producto", list(ids_por_nombre.keys()))
        tipo = st.selectbox("Tipo de movimiento", ["entrada", "salida"])
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
        enviado = st.form_submit_button("Registrar")

    if enviado:
        id_producto = int(ids_por_nombre[nombre])
        cantidad = int(cantidad)
        if tipo == "entrada":
            resultado = registrar_entrada(id_producto, cantidad)
        else:
            resultado = registrar_salida(id_producto, cantidad)
        # Guardar el mensaje y recargar para que los datos se actualicen
        st.session_state["mensaje"] = resultado
        st.rerun()


def pestana_inventario():
    st.header("Inventario actual")
    categorias = pd.read_sql_query(
        "SELECT DISTINCT categoria FROM productos ORDER BY categoria", conexion
    )["categoria"].tolist()
    elegida = st.selectbox("Filtrar por categoría", ["Todas"] + categorias)

    categoria = None if elegida == "Todas" else elegida
    st.dataframe(consultar_inventario(categoria), use_container_width=True)


def pestana_alertas():
    st.header("Alertas de stock bajo")
    minimo = st.slider("Stock mínimo", min_value=0, max_value=100, value=10)
    bajos = alertas_stock_bajo(minimo)

    if bajos.empty:
        st.info(f"No hay productos con stock menor a {minimo}.")
    else:
        st.dataframe(bajos, use_container_width=True)
        st.bar_chart(bajos.set_index("nombre")["stock"])


def main():
    st.set_page_config(page_title="SIGA - Grupo 9", page_icon="📦")
    st.title("📦 SIGA")
    tab_inicio, tab_registrar, tab_inventario, tab_alertas = st.tabs(
        ["Inicio", "Registrar movimiento", "Inventario", "Alertas"]
    )
    with tab_inicio:
        pestana_inicio()
    with tab_registrar:
        pestana_registrar()
    with tab_inventario:
        pestana_inventario()
    with tab_alertas:
        pestana_alertas()


if __name__ == "__main__":
    main()
