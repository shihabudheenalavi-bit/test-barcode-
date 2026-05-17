import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode

DB_NAME = "inventory.db"

st.set_page_config(page_title="Barcode Inventory App", layout="wide")

# ---------- DATABASE ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            barcode TEXT PRIMARY KEY,
            item_name TEXT,
            category TEXT,
            unit TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            barcode TEXT,
            item_name TEXT,
            movement_type TEXT,
            qty REAL,
            remarks TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_item(barcode, item_name, category, unit):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO items 
        (barcode, item_name, category, unit, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (barcode, item_name, category, unit, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def save_transaction(barcode, item_name, movement_type, qty, remarks):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO transactions
        (date, barcode, item_name, movement_type, qty, remarks)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        barcode,
        item_name,
        movement_type,
        qty,
        remarks
    ))
    conn.commit()
    conn.close()


def get_item(barcode):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM items WHERE barcode = ?", conn, params=(barcode,))
    conn.close()
    return df


def get_stock_report():
    conn = sqlite3.connect(DB_NAME)

    df = pd.read_sql_query("""
        SELECT 
            barcode,
            item_name,
            SUM(CASE WHEN movement_type = 'IN' THEN qty ELSE 0 END) AS total_in,
            SUM(CASE WHEN movement_type = 'OUT' THEN qty ELSE 0 END) AS total_out,
            SUM(CASE WHEN movement_type = 'IN' THEN qty ELSE -qty END) AS current_stock
        FROM transactions
        GROUP BY barcode, item_name
        ORDER BY item_name
    """, conn)

    conn.close()
    return df


def get_transactions():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY id DESC", conn)
    conn.close()
    return df


def scan_barcode(image):
    img = Image.open(image)
    decoded = decode(img)

    if decoded:
        return decoded[0].data.decode("utf-8")
    return None


init_db()

# ---------- UI ----------
st.title("📦 Mobile Barcode Inventory App")

menu = st.sidebar.radio(
    "Menu",
    ["Scan Barcode", "Add / Update Item", "Stock Report", "Transaction History"]
)

# ---------- SCAN BARCODE ----------
if menu == "Scan Barcode":
    st.subheader("📷 Scan Barcode Using Mobile Camera")

    camera_image = st.camera_input("Open camera and scan barcode")

    scanned_barcode = None

    if camera_image:
        scanned_barcode = scan_barcode(camera_image)

        if scanned_barcode:
            st.success(f"Barcode Scanned: {scanned_barcode}")
        else:
            st.error("Barcode not detected. Try again with better light and focus.")

    manual_barcode = st.text_input("Or enter barcode manually")

    barcode = scanned_barcode if scanned_barcode else manual_barcode

    if barcode:
        item_df = get_item(barcode)

        if not item_df.empty:
            item_name = item_df.iloc[0]["item_name"]
            st.info(f"Item Found: {item_name}")

            movement_type = st.selectbox("Movement Type", ["IN", "OUT"])
            qty = st.number_input("Quantity", min_value=0.0, step=1.0)
            remarks = st.text_area("Remarks")

            if st.button("Save Transaction"):
                if qty <= 0:
                    st.warning("Please enter quantity.")
                else:
                    save_transaction(barcode, item_name, movement_type, qty, remarks)
                    st.success("Transaction saved successfully.")

        else:
            st.warning("Item not found. Please add this item first.")

# ---------- ADD ITEM ----------
elif menu == "Add / Update Item":
    st.subheader("➕ Add / Update Inventory Item")

    barcode = st.text_input("Barcode")
    item_name = st.text_input("Item Name")
    category = st.text_input("Category", placeholder="Example: Gloves, Implant, Ortho, Consumable")
    unit = st.text_input("Unit", placeholder="Example: pcs, box, packet, set")

    if st.button("Save Item"):
        if barcode and item_name:
            save_item(barcode, item_name, category, unit)
            st.success("Item saved successfully.")
        else:
            st.warning("Barcode and item name are required.")

# ---------- STOCK REPORT ----------
elif menu == "Stock Report":
    st.subheader("📊 Stock Report")

    df = get_stock_report()

    if df.empty:
        st.info("No stock transactions available.")
    else:
        st.dataframe(df, use_container_width=True)

        excel_file = "stock_report.xlsx"
        df.to_excel(excel_file, index=False)

        with open(excel_file, "rb") as file:
            st.download_button(
                "Download Stock Report Excel",
                file,
                file_name="stock_report.xlsx"
            )

# ---------- TRANSACTION HISTORY ----------
elif menu == "Transaction History":
    st.subheader("📜 Transaction History")

    df = get_transactions()

    if df.empty:
        st.info("No transactions found.")
    else:
        st.dataframe(df, use_container_width=True)