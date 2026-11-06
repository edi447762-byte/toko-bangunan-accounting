import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date
import json

# ==================== KONFIGURASI ====================
st.set_page_config(
    page_title="Akuntansi Toko Bangunan",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# File paths
F_PRODUK   = f"{DATA_DIR}/produk.csv"
F_TRANSAKSI= f"{DATA_DIR}/transaksi.csv"
F_JURNAL   = f"{DATA_DIR}/jurnal.csv"
F_BUKUBESAR= f"{DATA_DIR}/buku_besar.csv"
F_COA      = f"{DATA_DIR}/coa.csv"

# ==================== COA DEFAULT ====================
DEFAULT_COA = [
    # (kode, nama, tipe, saldo_normal)
    ("1001", "Kas", "Aset", "Debit"),
    ("1002", "Bank", "Aset", "Debit"),
    ("1101", "Piutang Usaha", "Aset", "Debit"),
    ("1201", "Persediaan Barang Dagang", "Aset", "Debit"),
    ("1301", "Perlengkapan", "Aset", "Debit"),
    ("1401", "Peralatan Toko", "Aset", "Debit"),
    ("2001", "Utang Usaha", "Kewajiban", "Kredit"),
    ("2002", "Utang Bank", "Kewajiban", "Kredit"),
    ("3001", "Modal Pemilik", "Ekuitas", "Kredit"),
    ("3002", "Prive", "Ekuitas", "Debit"),
    ("4001", "Penjualan", "Pendapatan", "Kredit"),
    ("4002", "Retur Penjualan", "Pendapatan", "Debit"),
    ("4003", "Potongan Penjualan", "Pendapatan", "Debit"),
    ("5001", "Harga Pokok Penjualan (HPP)", "Beban", "Debit"),
    ("5002", "Pembelian", "Beban", "Debit"),
    ("5003", "Retur Pembelian", "Beban", "Kredit"),
    ("6001", "Beban Gaji", "Beban", "Debit"),
    ("6002", "Beban Listrik & Air", "Beban", "Debit"),
    ("6003", "Beban Sewa", "Beban", "Debit"),
    ("6004", "Beban Transport", "Beban", "Debit"),
    ("6005", "Beban Lain-lain", "Beban", "Debit"),
]

# ==================== HELPER LOAD/SAVE ====================
def load_df(path, columns):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_df(df, path):
    df.to_csv(path, index=False)

def init_data():
    if not os.path.exists(F_COA):
        df = pd.DataFrame(DEFAULT_COA, columns=["kode","nama","tipe","saldo_normal"])
        save_df(df, F_COA)

    produk_cols = ["id_produk","nama_produk","satuan","harga_beli","harga_jual","stok"]
    transaksi_cols = ["id_trx","tanggal","tipe","id_produk","nama_produk","qty","harga_satuan","total","pelanggan","keterangan"]
    jurnal_cols = ["id_jurnal","tanggal","kode_akun","nama_akun","debit","kredit","keterangan","ref"]

    for path, cols in [(F_PRODUK,produk_cols),(F_TRANSAKSI,transaksi_cols),
                       (F_JURNAL,jurnal_cols),(F_BUKUBESAR,jurnal_cols)]:
        if not os.path.exists(path):
            save_df(pd.DataFrame(columns=cols), path)

init_data()

# ==================== FUNGSI JURNAL ====================
def next_id(df, col, prefix):
    if df.empty:
        return f"{prefix}001"
    nums = df[col].str.extract(r'(\d+)$')[0].astype(int)
    return f"{prefix}{int(nums.max())+1:03d}"

def catat_jurnal(entries):
    """
    entries = list of dict: {tanggal, kode_akun, debit, kredit, keterangan, ref}
    kode_akun akan dilookup ke COA untuk nama_akun
    """
    coa = load_df(F_COA, ["kode","nama","tipe","saldo_normal"])
    jurnal = load_df(F_JURNAL, ["id_jurnal","tanggal","kode_akun","nama_akun","debit","kredit","keterangan","ref"])
    jid = next_id(jurnal, "id_jurnal", "J")
    rows = []
    for e in entries:
        row_coa = coa[coa["kode"]==e["kode_akun"]]
        nama = row_coa["nama"].values[0] if not row_coa.empty else "Unknown"
        rows.append({
            "id_jurnal": jid,
            "tanggal": e["tanggal"],
            "kode_akun": e["kode_akun"],
            "nama_akun": nama,
            "debit": float(e.get("debit",0)),
            "kredit": float(e.get("kredit",0)),
            "keterangan": e.get("keterangan",""),
            "ref": e.get("ref","")
        })
    jurnal = pd.concat([jurnal, pd.DataFrame(rows)], ignore_index=True)
    save_df(jurnal, F_JURNAL)
    save_df(jurnal, F_BUKUBESAR)  # buku besar = mirror jurnal (simple)
    return jid

# ==================== SIDEBAR NAV ====================
st.sidebar.title("🏗️ Toko Bangunan")
st.sidebar.caption("Sistem Akuntansi Usaha Dagang")
menu = st.sidebar.radio("Navigasi", [
    "📊 Dashboard",
    "📦 Master Produk",
    "🛒 Transaksi Penjualan",
    "📥 Transaksi Pembelian",
    "📝 Jurnal Umum",
    "📒 Buku Besar",
    "⚖️ Neraca Saldo",
    "📈 Laporan Laba Rugi",
    "🏦 Laporan Posisi Keuangan",
])

st.sidebar.markdown("---")
st.sidebar.info("💡 Data disimpan di folder `data/` sebagai CSV. Untuk produksi, gunakan database.")

# ==================== 1. DASHBOARD ====================
if menu == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.caption(f"Tanggal hari ini: {date.today().strftime('%d %B %Y')}")

    transaksi = load_df(F_TRANSAKSI, ["id_trx","tanggal","tipe","id_produk","nama_produk","qty","harga_satuan","total","pelanggan","keterangan"])
    produk = load_df(F_PRODUK, ["id_produk","nama_produk","satuan","harga_beli","harga_jual","stok"])
    jurnal = load_df(F_JURNAL, ["id_jurnal","tanggal","kode_akun","nama_akun","debit","kredit","keterangan","ref"])

    total_penjualan = transaksi[transaksi["tipe"]=="JUAL"]["total"].sum() if not transaksi.empty else 0
    total_pembelian = transaksi[transaksi["tipe"]=="BELI"]["total"].sum() if not transaksi.empty else 0
    total_produk = len(produk)
    stok_rendah = len(produk[produk["stok"] < 10]) if not produk.empty else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💰 Total Penjualan", f"Rp {total_penjualan:,.0f}")
    c2.metric("🛍️ Total Pembelian", f"Rp {total_pembelian:,.0f}")
    c3.metric("📦 Jumlah Produk", total_produk)
    c4.metric("⚠️ Stok Rendah (<10)", stok_rendah)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Tren Penjualan")
        if not transaksi.empty:
            jual = transaksi[transaksi["tipe"]=="JUAL"].copy()
            if not jual.empty:
                jual["tanggal"] = pd.to_datetime(jual["tanggal"])
                daily = jual.groupby("tanggal")["total"].sum().reset_index()
                fig = px.line(daily, x="tanggal", y="total", markers=True,
                              labels={"tanggal":"Tanggal","total":"Penjualan (Rp)"})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Belum ada data penjualan.")
        else:
            st.info("Belum ada transaksi.")

    with col2:
        st.subheader("📦 Stok Produk")
        if not produk.empty:
            fig = px.bar(produk.sort_values("stok").tail(10), x="stok", y="nama_produk",
                         orientation="h", labels={"stok":"Stok","nama_produk":"Produk"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada produk.")

    st.subheader("🧾 5 Transaksi Terakhir")
    if not transaksi.empty:
        st.dataframe(transaksi.tail(5).iloc[::-1], use_container_width=True)
    else:
        st.info("Belum ada transaksi.")

# ==================== 2. MASTER PRODUK ====================
elif menu == "📦 Master Produk":
    st.title("📦 Master Produk")
    produk = load_df(F_PRODUK, ["id_produk","nama_produk","satuan","harga_beli","harga_jual","stok"])

    with st.expander("➕ Tambah Produk Baru", expanded=False):
        with st.form("form_produk"):
            c1,c2 = st.columns(2)
            nama = c1.text_input("Nama Produk *")
            satuan = c2.selectbox("Satuan", ["Sak","Batang","Lembar","Buah","Kg","Meter","Pcs"])
            c3,c4 = st.columns(2)
            h_beli = c3.number_input("Harga Beli (Rp)", min_value=0, step=1000)
            h_jual = c4.number_input("Harga Jual (Rp)", min_value=0, step=1000)
            stok = st.number_input("Stok Awal", min_value=0, step=1)
            submit = st.form_submit_button("💾 Simpan Produk")
            if submit:
                if not nama.strip():
                    st.error("Nama produk wajib diisi.")
                else:
                    new_id = next_id(produk, "id_produk", "P") if not produk.empty else "P001"
                    row = pd.DataFrame([{
                        "id_produk": new_id, "nama_produk": nama, "satuan": satuan,
                        "harga_beli": h_beli, "harga_jual": h_jual, "stok": stok
                    }])
                    produk = pd.concat([produk, row], ignore_index=True)
                    save_df(produk, F_PRODUK)
                    st.success(f"Produk '{nama}' tersimpan ({new_id}).")
                    st.rerun()

    st.markdown("### 📋 Daftar Produk")
    if produk.empty:
        st.info("Belum ada produk. Tambahkan dulu.")
    else:
        search = st.text_input("🔍 Cari produk...")
        filtered = produk[produk["nama_produk"].str.contains(search, case=False)] if search else produk
        st.dataframe(filtered, use_container_width=True)

        st.markdown("### ✏️ Edit / Hapus Produk")
        pilihan = st.selectbox("Pilih Produk", produk["nama_produk"] + " (" + produk["id_produk"] + ")")
        if pilihan:
            idx = (produk["nama_produk"] + " (" + produk["id_produk"] + ")").tolist().index(pilihan)
            row = produk.iloc[idx]
            with st.form("edit_produk"):
                c1,c2 = st.columns(2)
                n_nama = c1.text_input("Nama", row["nama_produk"])
                n_sat = c2.text_input("Satuan", row["satuan"])
                c3,c4,c5 = st.columns(3)
                n_beli = c3.number_input("Harga Beli", value=int(row["harga_beli"]), step=1000)
                n_jual = c4.number_input("Harga Jual", value=int(row["harga_jual"]), step=1000)
                n_stok = c5.number_input("Stok", value=int(row["stok"]), step=1)
                c_btn1, c_btn2 = st.columns(2)
                update = c_btn1.form_submit_button("💾 Update")
                hapus = c_btn2.form_submit_button("🗑️ Hapus")
                if update:
                    produk.at[idx, "nama_produk"] = n_nama
                    produk.at[idx, "satuan"] = n_sat
                    produk.at[idx, "harga_beli"] = n_beli
                    produk.at[idx, "harga_jual"] = n_jual
                    produk.at[idx, "stok"] = n_stok
                    save_df(produk, F_PRODUK)
                    st.success("Produk diperbarui.")
                    st.rerun()
                if hapus:
                    produk = produk.drop(idx).reset_index(drop=True)
                    save_df(produk, F_PRODUK)
                    st.warning("Produk dihapus.")
                    st.rerun()

# ==================== 3. PENJUALAN ====================
elif menu == "🛒 Transaksi Penjualan":
    st.title("🛒 Transaksi Penjualan")
    produk = load_df(F_PRODUK, ["id_produk","nama_produk","satuan","harga_beli","harga_jual","stok"])
    transaksi = load_df(F_TRANSAKSI, ["id_trx","tanggal","tipe","id_produk","nama_produk","qty","harga_satuan","total","pelanggan","keterangan"])

    if produk.empty:
        st.warning("Tambahkan produk terlebih dahulu di menu Master Produk.")
    else:
        with st.form("form_jual"):
            tanggal = st.date_input("Tanggal", date.today())
            produk_pilihan = st.selectbox(
                "Produk",
                produk["nama_produk"] + " (" + produk["id_produk"] + ")"
            )
            idx_prod = (produk["nama_produk"] + " (" + produk["id_produk"] + ")").tolist().index(produk_pilihan)
            produk_row = produk.iloc[idx_prod]
            st.info(f"Stok tersedia: **{int(produk_row['stok'])} {produk_row['satuan']}** | Harga jual: **Rp {int(produk_row['harga_jual']):,}**")
            qty = st.number_input("Qty", min_value=1, step=1, value=1)
            harga = st.number_input("Harga Jual (Rp)", min_value=0, value=int(produk_row["harga_jual"]), step=1000)
            pelanggan = st.text_input("Pelanggan", value="Umum")
            metode = st.selectbox("Metode Pembayaran", ["Tunai","Kredit"])
            ket = st.text_area("Keterangan", value="")
            submit = st.form_submit_button("💾 Simpan Penjualan")

            if submit:
                if qty > produk_row["stok"]:
                    st.error(f"Stok tidak cukup. Sisa: {int(produk_row['stok'])}")
                else:
                    total = qty * harga
                    new_trx = next_id(transaksi, "id_trx", "T") if not transaksi.empty else "T001"
                    row = pd.DataFrame([{
                        "id_trx": new_trx,
                        "tanggal": str(tanggal),
                        "tipe": "JUAL",
                        "id_produk": produk_row["id_produk"],
                        "nama_produk": produk_row["nama_produk"],
                        "qty": qty,
                        "harga_satuan": harga,
                        "total": total,
                        "pelanggan": pelanggan,
                        "keterangan": ket
                    }])
                    transaksi = pd.concat([transaksi, row], ignore_index=True)
                    save_df(transaksi, F_TRANSAKSI)

                    # Update stok
                    produk.at[idx_prod, "stok"] = int(produk_row["stok"]) - qty
                    save_df(produk, F_PRODUK)

                    # Jurnal
                    hpp = int(produk_row["harga_beli"]) * qty
                    if metode == "Tunai":
                        akun_debit = "1001"
                    else:
                        akun_debit = "1101"
                    entries = [
                        {"tanggal":str(tanggal),"kode_akun":akun_debit,"debit":total,"kredit":0,
                         "keterangan":f"Penjualan {produk_row['nama_produk']} x{qty}","ref":new_trx},
                        {"tanggal":str(tanggal),"kode_akun":"4001","debit":0,"kredit":total,
                         "keterangan":f"Penjualan {produk_row['nama_produk']} x{qty}","ref":new_trx},
                        {"tanggal":str(tanggal),"kode_akun":"5001","debit":hpp,"kredit":0,
                         "keterangan":f"HPP {produk_row['nama_produk']} x{qty}","ref":new_trx},
                        {"tanggal":str(tanggal),"kode_akun":"1201","debit":0,"kredit":hpp,
                         "keterangan":f"Pengurangan persediaan {produk_row['nama_produk']}","ref":new_trx},
                    ]
                    catat_jurnal(entries)
                    st.success(f"✅ Penjualan {new_trx} tersimpan. Total: Rp {total:,}")
                    st.rerun()

    st.markdown("### 📋 Riwayat Penjualan")
    jual = transaksi[transaksi["tipe"]=="JUAL"] if not transaksi.empty else pd.DataFrame()
    if jual.empty:
        st.info("Belum ada penjualan.")
    else:
        st.dataframe(jual.iloc[::-1], use_container_width=True)

# ==================== 4. PEMBELIAN ====================
elif menu == "📥 Transaksi Pembelian":
    st.title("📥 Transaksi Pembelian")
    produk = load_df(F_PRODUK, ["id_produk","nama_produk","satuan","harga_beli","harga_jual","stok"])
    transaksi = load_df(F_TRANSAKSI, ["id_trx","tanggal","tipe","id_produk","nama_produk","qty","harga_satuan","total","pelanggan","keterangan"])

    if produk.empty:
        st.warning("Tambahkan produk dulu di Master Produk.")
    else:
        with st.form("form_beli"):
            tanggal = st.date_input("Tanggal", date.today())
            produk_pilihan = st.selectbox(
                "Produk",
                produk["nama_produk"] + " (" + produk["id_produk"] + ")"
            )
            idx_prod = (produk["nama_produk"] + " (" + produk["id_produk"] + ")").tolist().index(produk_pilihan)
            produk_row = produk.iloc[idx_prod]
            qty = st.number_input("Qty", min_value=1, step=1, value=1)
            harga = st.number_input("Harga Beli (Rp)", min_value=0, value=int(produk_row["harga_beli"]), step=1000)
            supplier = st.text_input("Supplier", value="Umum")
            metode = st.selectbox("Metode Pembayaran", ["Tunai","Kredit"])
            ket = st.text_area("Keterangan", value="")
            submit = st.form_submit_button("💾 Simpan Pembelian")

            if submit:
                total = qty * harga
                new_trx = next_id(transaksi, "id_trx", "T") if not transaksi.empty else "T001"
                row = pd.DataFrame([{
                    "id_trx": new_trx,
                    "tanggal": str(tanggal),
                    "tipe": "BELI",
                    "id_produk": produk_row["id_produk"],
                    "nama_produk": produk_row["nama_produk"],
                    "qty": qty,
                    "harga_satuan": harga,
                    "total": total,
                    "pelanggan": supplier,
                    "keterangan": ket
                }])
                transaksi = pd.concat([transaksi, row], ignore_index=True)
                save_df(transaksi, F_TRANSAKSI)

                # Update stok & harga beli rata-rata
                stok_lama = int(produk_row["stok"])
                stok_baru = stok_lama + qty
                hb_lama = int(produk_row["harga_beli"])
                hb_baru = ((stok_lama * hb_lama) + (qty * harga)) / stok_baru if stok_baru > 0 else harga
                produk.at[idx_prod, "stok"] = stok_baru
                produk.at[idx_prod, "harga_beli"] = int(hb_baru)
                save_df(produk, F_PRODUK)

                # Jurnal
                if metode == "Tunai":
                    akun_kredit = "1001"
                else:
                    akun_kredit = "2001"
                entries = [
                    {"tanggal":str(tanggal),"kode_akun":"1201","debit":total,"kredit":0,
                     "keterangan":f"Pembelian {produk_row['nama_produk']} x{qty}","ref":new_trx},
                    {"tanggal":str(tanggal),"kode_akun":akun_kredit,"debit":0,"kredit":total,
                     "keterangan":f"Pembelian {produk_row['nama_produk']} x{qty}","ref":new_trx},
                ]
                catat_jurnal(entries)
                st.success(f"✅ Pembelian {new_trx} tersimpan. Total: Rp {total:,}")
                st.rerun()

    st.markdown("### 📋 Riwayat Pembelian")
    beli = transaksi[transaksi["tipe"]=="BELI"] if not transaksi.empty else pd.DataFrame()
    if beli.empty:
        st.info("Belum ada pembelian.")
    else:
        st.dataframe(beli.iloc[::-1], use_container_width=True)

# ==================== 5. JURNAL UMUM ====================
elif menu == "📝 Jurnal Umum":
    st.title("📝 Jurnal Umum")
    jurnal = load_df(F_JURNAL, ["id_jurnal","tanggal","kode_akun","nama_akun","debit","kredit","keterangan","ref"])
    coa = load_df(F_COA, ["kode","nama","tipe","saldo_normal"])

    with st.expander("➕ Input Jurnal Manual"):
        with st.form("form_jurnal"):
            tanggal = st.date_input("Tanggal", date.today())
            coa_options = coa["kode"] + " - " + coa["nama"]
            st.markdown("**Baris Debit**")
            c1,c2 = st.columns(2)
            akun_debit = c1.selectbox("Akun Debit", coa_options, key="jd")
            nominal_debit = c2.number_input("Nominal Debit", min_value=0, step=1000, key="nd")
            st.markdown("**Baris Kredit**")
            c3,c4 = st.columns(2)
            akun_kredit = c3.selectbox("Akun Kredit", coa_options, key="jk")
            nominal_kredit = c4.number_input("Nominal Kredit", min_value=0, step=1000, key="nk")
            ket = st.text_input("Keterangan")
            submit = st.form_submit_button("💾 Simpan Jurnal")

            if submit:
                if nominal_debit == 0 or nominal_kredit == 0:
                    st.error("Nominal tidak boleh 0.")
                elif nominal_debit != nominal_kredit:
                    st.error("Total debit dan kredit harus sama (balance)!")
                else:
                    entries = [
                        {"tanggal":str(tanggal),"kode_akun":akun_debit.split(" - ")[0],
               
