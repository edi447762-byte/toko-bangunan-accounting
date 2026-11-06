"""
Migrasi data dari CSV (folder data/) ke database baru.
Jalankan sekali:  python migrate_csv.py
Hapus file CSV setelah migrasi sukses.
"""
import os
import pandas as pd
from models import init_db, insert_produk, insert_transaksi, catat_jurnal, execute, fetch_df
from database import get_conn

DATA_DIR = "data"
F_PRODUK   = f"{DATA_DIR}/produk.csv"
F_TRANSAKSI= f"{DATA_DIR}/transaksi.csv"
F_JURNAL   = f"{DATA_DIR}/jurnal.csv"

def _read(path):
    return pd.read_csv(path) if os.path.exists(path) else None

def migrate():
    print("⏳ Init database...")
    init_db()
    print("✅ Skema siap.")

    # ---- Produk ----
    df = _read(F_PRODUK)
    if df is not None and not df.empty:
        existing = fetch_df("SELECT id_produk FROM produk")["id_produk"].tolist()
        rows = df[~df["id_produk"].isin(existing)].to_dict("records")
        for r in rows:
            execute(
                """INSERT INTO produk (id_produk, nama_produk, satuan, harga_beli, harga_jual, stok)
                   VALUES (:id_produk, :nama_produk, :satuan, :harga_beli, :harga_jual, :stok)""",
                r,
            )
        print(f"✅ Produk: {len(rows)} baris dimigrasi.")
    else:
        print("ℹ️  produk.csv tidak ada / kosong.")

    # ---- Transaksi ----
    df = _read(F_TRANSAKSI)
    if df is not None and not df.empty:
        # rename pelanggan -> pihak
        if "pelanggan" in df.columns:
            df = df.rename(columns={"pelanggan": "pihak"})
        existing = fetch_df("SELECT id_trx FROM transaksi")["id_trx"].tolist()
        rows = df[~df["id_trx"].isin(existing)].to_dict("records")
        for r in rows:
            execute(
                """INSERT INTO transaksi (id_trx, tanggal, tipe, id_produk, nama_produk, qty,
                   harga_satuan, total, pihak, keterangan)
                   VALUES (:id_trx, :tanggal, :tipe, :id_produk, :nama_produk, :qty,
                           :harga_satuan, :total, :pihak, :keterangan)""",
                r,
            )
        print(f"✅ Transaksi: {len(rows)} baris dimigrasi.")
    else:
        print("ℹ️  transaksi.csv tidak ada / kosong.")

    # ---- Jurnal ----
    df = _read(F_JURNAL)
    if df is not None and not df.empty:
        # jurnal.csv lama punya id_jurnal yang sudah dipakai -> insert apa adanya
        existing = fetch_df("SELECT id_jurnal, kode_akun, debit, kredit FROM jurnal")
        rows = []
        for r in df.to_dict("records"):
            dup = existing[
                (existing["id_jurnal"] == r["id_jurnal"]) &
                (existing["kode_akun"] == r["kode_akun"]) &
                (abs(existing["debit"] - float(r["debit"])) < 0.01) &
                (abs(existing["kredit"] - float(r["kredit"])) < 0.01)
            ]
            if dup.empty:
                rows.append(r)
        if rows:
            with get_conn() as conn:
                conn.exec_driver_sql(
                    """INSERT INTO jurnal (id_jurnal, tanggal, kode_akun, nama_akun, debit, kredit, keterangan, ref)
                       VALUES (:id_jurnal, :tanggal, :kode_akun, :nama_akun, :debit, :kredit, :keterangan, :ref)""",
                    rows,
                )
        print(f"✅ Jurnal: {len(rows)} baris dimigrasi.")
    else:
        print("ℹ️  jurnal.csv tidak ada / kosong.")

    print("\n🎉 Migrasi selesai. Database:", os.getenv("DATABASE_URL", "sqlite:///data/toko_bangunan.db"))

if __name__ == "__main__":
    migrate()
