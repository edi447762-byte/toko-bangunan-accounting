import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import os
from dotenv import load_dotenv

# Load .env (untuk lokal)
load_dotenv()

import models
from database import DATABASE_URL

st.set_page_config(
    page_title="Akuntansi Toko Bangunan",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Init DB sekali per proses
@st.cache_resource
def _init():
    models.init_db()
    return True
_init()

# ==================== SIDEBAR ====================
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
db_label = "SQLite" if DATABASE_URL.startswith("sqlite") else "PostgreSQL"
st.sidebar.success(f"🗄️ Database: **{db_label}**")
st.sidebar.caption(DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)

# ==================== 1. DASHBOARD ====================
if menu == "📊 Dashboard":
    st.title("📊 Dashboard")
    st.caption(f"Tanggal hari ini: {date.today().strftime('%d %B %Y')}")

    produk = models.get_produk()
    total_penjualan = models.total_penjualan()
    total_pembelian = models.total_pembelian()
    stok_rendah = int((produk["stok"] < 10).sum()) if not produk.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Penjualan", f"Rp {total_penjualan:,.0f}")
    c2.metric("🛍️ Total Pembelian", f"Rp {total_pembelian:,.0f}")
    c3.metric("📦 Jumlah Produk", len(produk))
    c4.metric("⚠️ Stok Rendah (<10)", stok_rendah)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Tren Penjualan")
        tren = models.tren_penjualan()
        if not tren.empty:
            tren["tanggal"] = pd.to_datetime(tren["tanggal"])
            fig = px.line(tren, x="tanggal", y="total", markers=True,
                          labels={"tanggal": "Tanggal", "total": "Penjualan (Rp)"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada penjualan.")

    with col2:
        st.subheader("📦 Stok Produk")
        if not produk.empty:
            fig = px.bar(produk.sort_values("stok").tail(10), x="stok", y="nama_produk",
                         orientation="h", labels={"stok": "Stok", "nama_produk": "Produk"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada produk.")

    st.subheader("🧾 5 Transaksi Terakhir")
    trx = models.get_transaksi()
    if not trx.empty:
        st.dataframe(trx.head(5), use_container_width=True)
    else:
        st.info("Belum ada transaksi.")

# ==================== 2. MASTER PRODUK ====================
elif menu == "📦 Master Produk":
    st.title("📦 Master Produk")
    produk = models.get_produk()

    with st.expander("➕ Tambah Produk Baru", expanded=produk.empty):
        with st.form("form_produk"):
            c1, c2 = st.columns(2)
            nama = c1.text_input("Nama Produk *")
            satuan = c2.selectbox("Satuan", ["Sak", "Batang", "Lembar", "Buah", "Kg", "Meter", "Pcs"])
            c3, c4 = st.columns(2)
            h_beli = c3.number_input("Harga Beli (Rp)", min_value=0, step=1000)
            h_jual = c4.number_input("Harga Jual (Rp)", min_value=0, step=1000)
            stok = st.number_input("Stok Awal", min_value=0, step=1)
            if st.form_submit_button("💾 Simpan Produk"):
                if not nama.strip():
                    st.error("Nama produk wajib diisi.")
                else:
                    new_id = models.insert_produk(nama, satuan, h_beli, h_jual, stok)
                    st.success(f"Produk '{nama}' tersimpan ({new_id}).")
                    st.rerun()

    st.markdown("### 📋 Daftar Produk")
    if produk.empty:
        st.info("Belum ada produk.")
    else:
        search = st.text_input("🔍 Cari produk...")
        filtered = produk[produk["nama_produk"].str.contains(search, case=False)] if search else produk
        st.dataframe(filtered, use_container_width=True)

        st.markdown("### ✏️ Edit / Hapus Produk")
        labels = produk["nama_produk"] + " (" + produk["id_produk"] + ")"
        pilihan = st.selectbox("Pilih Produk", labels)
        idx = labels.tolist().index(pilihan)
        row = produk.iloc[idx]

        with st.form("edit_produk"):
            c1, c2 = st.columns(2)
            n_nama = c1.text_input("Nama", row["nama_produk"])
            n_sat = c2.text_input("Satuan", row["satuan"])
            c3, c4, c5 = st.columns(3)
            n_beli = c3.number_input("Harga Beli", value=int(row["harga_beli"]), step=1000)
            n_jual = c4.number_input("Harga Jual", value=int(row["harga_jual"]), step=1000)
            n_stok = c5.number_input("Stok", value=int(row["stok"]), step=1)
            c_b1, c_b2 = st.columns(2)
            update = c_b1.form_submit_button("💾 Update")
            hapus = c_b2.form_submit_button("🗑️ Hapus")
            if update:
                models.update_produk(row["id_produk"], n_nama, n_sat, n_beli, n_jual, n_stok)
                st.success("Produk diperbarui.")
                st.rerun()
            if hapus:
                models.delete_produk(row["id_produk"])
                st.warning("Produk dihapus.")
                st.rerun()

# ==================== 3. PENJUALAN ====================
elif menu == "🛒 Transaksi Penjualan":
    st.title("🛒 Transaksi Penjualan")
    produk = models.get_produk()

    if produk.empty:
        st.warning("Tambahkan produk terlebih dahulu.")
    else:
        with st.form("form_jual"):
            tanggal = st.date_input("Tanggal", date.today())
            labels = produk["nama_produk"] + " (" + produk["id_produk"] + ")"
            pilihan = st.selectbox("Produk", labels)
            idx = labels.tolist().index(pilihan)
            prow = produk.iloc[idx]
            st.info(f"Stok: **{int(prow['stok'])} {prow['satuan']}** | Harga: **Rp {int(prow['harga_jual']):,}**")
            qty = st.number_input("Qty", min_value=1, step=1, value=1)
            harga = st.number_input("Harga Jual (Rp)", min_value=0, value=int(prow["harga_jual"]), step=1000)
            pelanggan = st.text_input("Pelanggan", value="Umum")
            metode = st.selectbox("Metode Pembayaran", ["Tunai", "Kredit"])
            ket = st.text_area("Keterangan", value="")
            submit = st.form_submit_button("💾 Simpan Penjualan")

            if submit:
                if qty > int(prow["stok"]):
                    st.error(f"Stok tidak cukup. Sisa: {int(prow['stok'])}")
                else:
                    total = qty * harga
                    new_trx = models.insert_transaksi(
                        "JUAL", tanggal, prow["id_produk"], prow["nama_produk"],
                        qty, harga, total, pelanggan, ket,
                    )
                    models.update_stok(prow["id_produk"], int(prow["stok"]) - qty)

                    hpp = int(prow["harga_beli"]) * qty
                    akun_debit = "1001" if metode == "Tunai" else "1101"
                    models.catat_jurnal([
                        {"tanggal": str(tanggal), "kode_akun": akun_debit, "debit": total, "kredit": 0,
                         "keterangan": f"Penjualan {prow['nama_produk']} x{qty}", "ref": new_trx},
                        {"tanggal": str(tanggal), "kode_akun": "4001", "debit": 0, "kredit": total,
                         "keterangan": f"Penjualan {prow['nama_produk']} x{qty}", "ref": new_trx},
                        {"tanggal": str(tanggal), "kode_akun": "5001", "debit": hpp, "kredit": 0,
                         "keterangan": f"HPP {prow['nama_produk']} x{qty}", "ref": new_trx},
                        {"tanggal": str(tanggal), "kode_akun": "1201", "debit": 0, "kredit": hpp,
                         "keterangan": f"Pengurangan persediaan {prow['nama_produk']}", "ref": new_trx},
                    ])
                    st.success(f"✅ Penjualan {new_trx} tersimpan. Total: Rp {total:,}")
                    st.rerun()

    st.markdown("### 📋 Riwayat Penjualan")
    jual = models.get_transaksi("JUAL")
    if jual.empty:
        st.info("Belum ada penjualan.")
    else:
        st.dataframe(jual, use_container_width=True)

# ==================== 4. PEMBELIAN ====================
elif menu == "📥 Transaksi Pembelian":
    st.title("📥 Transaksi Pembelian")
    produk = models.get_produk()

    if produk.empty:
        st.warning("Tambahkan produk dulu.")
    else:
        with st.form("form_beli"):
            tanggal = st.date_input("Tanggal", date.today())
            labels = produk["nama_produk"] + " (" + produk["id_produk"] + ")"
            pilihan = st.selectbox("Produk", labels)
            idx = labels.tolist().index(pilihan)
            prow = produk.iloc[idx]
            qty = st.number_input("Qty", min_value=1, step=1, value=1)
            harga = st.number_input("Harga Beli (Rp)", min_value=0, value=int(prow["harga_beli"]), step=1000)
            supplier = st.text_input("Supplier", value="Umum")
            metode = st.selectbox("Metode Pembayaran", ["Tunai", "Kredit"])
            ket = st.text_area("Keterangan", value="")
            submit = st.form_submit_button("💾 Simpan Pembelian")

            if submit:
                total = qty * harga
                new_trx = models.insert_transaksi(
                    "BELI", tanggal, prow["id_produk"], prow["nama_produk"],
                    qty, harga, total, supplier, ket,
                )
                stok_lama = int(prow["stok"])
                stok_baru = stok_lama + qty
                hb_lama = float(prow["harga_beli"])
                hb_baru = ((stok_lama * hb_lama) + (qty * harga)) / stok_baru if stok_baru > 0 else harga
                models.update_stok(prow["id_produk"], stok_baru, hb_baru)

                akun_kredit = "1001" if metode == "Tunai" else "2001"
                models.catat_jurnal([
                    {"tanggal": str(tanggal), "kode_akun": "1201", "debit": total, "kredit": 0,
                     "keterangan": f"Pembelian {prow['nama_produk']} x{qty}", "ref": new_trx},
                    {"tanggal": str(tanggal), "kode_akun": akun_kredit, "debit": 0, "kredit": total,
                     "keterangan": f"Pembelian {prow['nama_produk']} x{qty}", "ref": new_trx},
                ])
                st.success(f"✅ Pembelian {new_trx} tersimpan. Total: Rp {total:,}")
                st.rerun()

    st.markdown("### 📋 Riwayat Pembelian")
    beli = models.get_transaksi("BELI")
    if beli.empty:
        st.info("Belum ada pembelian.")
    else:
        st.dataframe(beli, use_container_width=True)

# ==================== 5. JURNAL UMUM ====================
elif menu == "📝 Jurnal Umum":
    st.title("📝 Jurnal Umum")
    coa = models.get_coa()
    jurnal = models.get_jurnal()

    with st.expander("➕ Input Jurnal Manual"):
        with st.form("form_jurnal"):
            tanggal = st.date_input("Tanggal", date.today())
            opts = coa["kode"] + " - " + coa["nama"]
            c1, c2 = st.columns(2)
            akun_d = c1.selectbox("Akun Debit", opts, key="jd")
            nom_d = c2.number_input("Nominal Debit", min_value=0, step=1000, key="nd")
            c3, c4 = st.columns(2)
            akun_k = c3.selectbox("Akun Kredit", opts, key="jk")
            nom_k = c4.number_input("Nominal Kredit", min_value=0, step=1000, key="nk")
            ket = st.text_input("Keterangan")
            if st.form_submit_button("💾 Simpan Jurnal"):
                if nom_d == 0 or nom_k == 0:
                    st.error("Nominal tidak boleh 0.")
                elif nom_d != nom_k:
                    st.error("Debit dan kredit harus sama!")
                else:
                    models.catat_jurnal([
                        {"tanggal": str(tanggal), "kode_akun": akun_d.split(" - ")[0],
                         "debit": nom_d, "kredit": 0, "keterangan": ket, "ref": "MANUAL"},
                        {"tanggal": str(tanggal), "kode_akun": akun_k.split(" - ")[0],
                         "debit": 0, "kredit": nom_k, "keterangan": ket, "ref": "MANUAL"},
                    ])
                    st.success("Jurnal tersimpan.")
                    st.rerun()

    st.markdown("### 📋 Daftar Jurnal")
    if jurnal.empty:
        st.info("Belum ada jurnal.")
    else:
        st.dataframe(jurnal.sort_values(["tanggal", "id_jurnal"], ascending=[False, False]),
                     use_container_width=True)
        td, tk = jurnal["debit"].sum(), jurnal["kredit"].sum()
        st.markdown(f"**Total Debit:** Rp {td:,.0f} | **Total Kredit:** Rp {tk:,.0f}")
        if abs(td - tk) < 0.01:
            st.success("✅ Jurnal balance.")
        else:
            st.error("❌ Jurnal TIDAK balance!")

# ==================== 6. BUKU BESAR ====================
elif menu == "📒 Buku Besar":
    st.title("📒 Buku Besar")
    coa = models.get_coa()
    jurnal = models.get_jurnal()

    if jurnal.empty:
        st.info("Belum ada jurnal.")
    else:
        jurnal["tanggal"] = pd.to_datetime(jurnal["tanggal"])
        opts = coa["kode"] + " - " + coa["nama"]
        pilih = st.selectbox("Pilih Akun", opts)
        kode = pilih.split(" - ")[0]
        nama_akun = coa[coa["kode"] == kode]["nama"].values[0]
        saldo_normal = coa[coa["kode"] == kode]["saldo_normal"].values[0]

        df = jurnal[jurnal["kode_akun"] == kode].sort_values("tanggal").copy()
        if df.empty:
            st.warning(f"Belum ada transaksi untuk akun {pilih}.")
        else:
            df["saldo"] = (df["debit"] - df["kredit"]).cumsum()
            td, tk = df["debit"].sum(), df["kredit"].sum()
            saldo_akhir = td - tk if saldo_normal == "Debit" else tk - td
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Debit", f"Rp {td:,.0f}")
            c2.metric("Total Kredit", f"Rp {tk:,.0f}")
            c3.metric("Saldo Akhir", f"Rp {abs(saldo_akhir):,.0f} ({saldo_normal})")
            st.dataframe(df[["tanggal", "id_jurnal", "keterangan", "debit", "kredit", "saldo"]],
                         use_container_width=True)

        st.markdown("---")
        st.markdown("### 📊 Ringkasan Semua Akun")
        ring = models.saldo_per_akun()
        ring = ring[(ring["total_debit"] != 0) | (ring["total_kredit"] != 0)]
        if not ring.empty:
            st.dataframe(ring[["kode", "nama", "tipe", "total_debit", "total_kredit", "saldo"]],
                         use_container_width=True)

# ==================== 7. NERACA SALDO ====================
elif menu == "⚖️ Neraca Saldo":
    st.title("⚖️ Neraca Saldo")
    ring = models.saldo_per_akun()
    ring = ring[(ring["total_debit"] != 0) | (ring["total_kredit"] != 0)]

    if ring.empty:
        st.info("Belum ada saldo.")
    else:
        rows = []
        for _, r in ring.iterrows():
            saldo = r["saldo"]
            if r["saldo_normal"] == "Debit":
                d = saldo if saldo > 0 else 0
                k = -saldo if saldo < 0 else 0
            else:
                k = saldo if saldo > 0 else 0
                d = -saldo if saldo < 0 else 0
            rows.append({"Kode": r["kode"], "Nama Akun": r["nama"], "Tipe": r["tipe"],
                         "Debit": d, "Kredit": k})
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        td, tk = df["Debit"].sum(), df["Kredit"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total Debit", f"Rp {td:,.0f}")
        c2.metric("Total Kredit", f"Rp {tk:,.0f}")
        if abs(td - tk) < 0.01:
            st.success("✅ Neraca Saldo Balance.")
        else:
            st.error("❌ Tidak balance, periksa jurnal.")

# ==================== 8. LABA RUGI ====================
elif menu == "📈 Laporan Laba Rugi":
    st.title("📈 Laporan Laba Rugi")
    ring = models.saldo_per_akun()

    pend = ring[ring["tipe"] == "Pendapatan"]
    beban = ring[ring["tipe"] == "Beban"]
    # Pendapatan: kredit - debit ; Beban: debit - kredit
    total_pend = (pend["total_kredit"] - pend["total_debit"]).sum()
    total_beban = (beban["total_debit"] - beban["total_kredit"]).sum()
    laba = total_pend - total_beban

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Pendapatan", f"Rp {total_pend:,.0f}")
    c2.metric("💸 Total Beban", f"Rp {total_beban:,.0f}")
    c3.metric("📊 Laba/Rugi Bersih", f"Rp {laba:,.0f}", delta="Laba" if laba >= 0 else "Rugi")

    st.markdown("---")
    st.subheader("Rincian Pendapatan")
    rp = pend[(pend["total_kredit"] - pend["total_debit"]) != 0]
    if not rp.empty:
        st.dataframe(pd.DataFrame({
            "Akun": rp["nama"],
            "Jumlah": rp["total_kredit"] - rp["total_debit"],
        }), use_container_width=True)

    st.subheader("Rincian Beban")
    rb = beban[(beban["total_debit"] - beban["total_kredit"]) != 0]
    if not rb.empty:
        st.dataframe(pd.DataFrame({
            "Akun": rb["nama"],
            "Jumlah": rb["total_debit"] - rb["total_kredit"],
        }), use_container_width=True)

# ==================== 9. POSISI KEUANGAN ====================
elif menu == "🏦 Laporan Posisi Keuangan":
    st.title("🏦 Laporan Posisi Keuangan (Neraca)")
    ring = models.saldo_per_akun()

    aset = ring[(ring["tipe"] == "Aset") & (ring["saldo"] != 0)]
    liab = ring[(ring["tipe"] == "Kewajiban") & (ring["saldo"] != 0)]
    ekuit = ring[(ring["tipe"] == "Ekuitas") & (ring["saldo"] != 0)]

    pend = ring[ring["tipe"] == "Pendapatan"]
    beban = ring[ring["tipe"] == "Beban"]
    laba = (pend["total_kredit"] - pend["total_debit"]).sum() - (beban["total_debit"] - beban["total_kredit"]).sum()

    total_aset = aset["saldo"].sum()
    total_liab = liab["saldo"].sum()
    total_ekuit = ekuit["saldo"].sum() + laba

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Aset", f"Rp {total_aset:,.0f}")
    c2.metric("📉 Total Kewajiban", f"Rp {total_liab:,.0f}")
    c3.metric("📈 Total Ekuitas", f"Rp {total_ekuit:,.0f}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("ASET")
        if not aset.empty:
            st.dataframe(aset[["nama", "saldo"]].rename(columns={"nama": "Akun", "saldo": "Saldo"}),
                         use_container_width=True)
        st.markdown(f"**Total Aset: Rp {total_aset:,.0f}**")
    with col2:
        st.subheader("KEWAJIBAN")
        if not liab.empty:
            st.dataframe(liab[["nama", "saldo"]].rename(columns={"nama": "Akun", "saldo": "Saldo"}),
                         use_container_width=True)
        st.markdown(f"**Total Kewajiban: Rp {total_liab:,.0f}**")
        st.subheader("EKUITAS")
        if not ekuit.empty:
            st.dataframe(ekuit[["nama", "saldo"]].rename(columns={"nama": "Akun", "saldo": "Saldo"}),
                         use_container_width=True)
        st.markdown(f"**Laba/Rugi Berjalan: Rp {laba:,.0f}**")
        st.markdown(f"**Total Ekuitas: Rp {total_ekuit:,.0f}**")
        st.markdown(f"**Total Kewajiban + Ekuitas: Rp {total_liab + total_ekuit:,.0f}**")

    if abs(total_aset - (total_liab + total_ekuit)) < 0.01:
        st.success("✅ Neraca Balance!")
    else:
        st.warning(f"⚠️ Selisih: Rp {abs(total_aset - (total_liab + total_ekuit)):,.0f}")
