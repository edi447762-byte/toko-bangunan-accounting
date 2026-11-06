"""
Skema database + fungsi CRUD.
Semua query pakai SQLAlchemy Core (text) agar portable SQLite/Postgres.
"""
import pandas as pd
from datetime import datetime
from database import engine, get_conn

# ==================== DDL ====================
DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS coa (
    kode        TEXT PRIMARY KEY,
    nama        TEXT NOT NULL,
    tipe        TEXT NOT NULL CHECK(tipe IN ('Aset','Kewajiban','Ekuitas','Pendapatan','Beban')),
    saldo_normal TEXT NOT NULL CHECK(saldo_normal IN ('Debit','Kredit'))
);

CREATE TABLE IF NOT EXISTS produk (
    id_produk   TEXT PRIMARY KEY,
    nama_produk TEXT NOT NULL,
    satuan      TEXT,
    harga_beli  REAL DEFAULT 0,
    harga_jual  REAL DEFAULT 0,
    stok        INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaksi (
    id_trx      TEXT PRIMARY KEY,
    tanggal     DATE NOT NULL,
    tipe        TEXT NOT NULL CHECK(tipe IN ('JUAL','BELI')),
    id_produk   TEXT,
    nama_produk TEXT,
    qty         INTEGER NOT NULL,
    harga_satuan REAL NOT NULL,
    total       REAL NOT NULL,
    pihak       TEXT,              -- pelanggan (jual) / supplier (beli)
    keterangan  TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_produk) REFERENCES produk(id_produk)
);

CREATE TABLE IF NOT EXISTS jurnal (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_jurnal   TEXT NOT NULL,
    tanggal     DATE NOT NULL,
    kode_akun   TEXT NOT NULL,
    nama_akun   TEXT NOT NULL,
    debit       REAL DEFAULT 0,
    kredit      REAL DEFAULT 0,
    keterangan  TEXT,
    ref         TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kode_akun) REFERENCES coa(kode)
);

CREATE INDEX IF NOT EXISTS idx_jurnal_tanggal ON jurnal(tanggal);
CREATE INDEX IF NOT EXISTS idx_jurnal_akun    ON jurnal(kode_akun);
CREATE INDEX IF NOT EXISTS idx_jurnal_id      ON jurnal(id_jurnal);
CREATE INDEX IF NOT EXISTS idx_transaksi_tgl  ON transaksi(tanggal);
"""

DDL_POSTGRES = """
CREATE TABLE IF NOT EXISTS coa (
    kode        VARCHAR(10) PRIMARY KEY,
    nama        VARCHAR(100) NOT NULL,
    tipe        VARCHAR(20) NOT NULL CHECK(tipe IN ('Aset','Kewajiban','Ekuitas','Pendapatan','Beban')),
    saldo_normal VARCHAR(10) NOT NULL CHECK(saldo_normal IN ('Debit','Kredit'))
);

CREATE TABLE IF NOT EXISTS produk (
    id_produk   VARCHAR(20) PRIMARY KEY,
    nama_produk VARCHAR(200) NOT NULL,
    satuan      VARCHAR(20),
    harga_beli  NUMERIC(15,2) DEFAULT 0,
    harga_jual  NUMERIC(15,2) DEFAULT 0,
    stok        INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaksi (
    id_trx      VARCHAR(20) PRIMARY KEY,
    tanggal     DATE NOT NULL,
    tipe        VARCHAR(10) NOT NULL CHECK(tipe IN ('JUAL','BELI')),
    id_produk   VARCHAR(20),
    nama_produk VARCHAR(200),
    qty         INTEGER NOT NULL,
    harga_satuan NUMERIC(15,2) NOT NULL,
    total       NUMERIC(15,2) NOT NULL,
    pihak       VARCHAR(100),
    keterangan  TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_produk) REFERENCES produk(id_produk)
);

CREATE TABLE IF NOT EXISTS jurnal (
    id          SERIAL PRIMARY KEY,
    id_jurnal   VARCHAR(20) NOT NULL,
    tanggal     DATE NOT NULL,
    kode_akun   VARCHAR(10) NOT NULL,
    nama_akun   VARCHAR(100) NOT NULL,
    debit       NUMERIC(15,2) DEFAULT 0,
    kredit      NUMERIC(15,2) DEFAULT 0,
    keterangan  TEXT,
    ref         VARCHAR(30),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (kode_akun) REFERENCES coa(kode)
);

CREATE INDEX IF NOT EXISTS idx_jurnal_tanggal ON jurnal(tanggal);
CREATE INDEX IF NOT EXISTS idx_jurnal_akun    ON jurnal(kode_akun);
CREATE INDEX IF NOT EXISTS idx_jurnal_id      ON jurnal(id_jurnal);
CREATE INDEX IF NOT EXISTS idx_transaksi_tgl  ON transaksi(tanggal);
"""

def is_sqlite() -> bool:
    from database import DATABASE_URL
    return DATABASE_URL.startswith("sqlite")

def init_db():
    """Buat tabel + seed COA jika belum ada."""
    ddl = DDL_SQLITE if is_sqlite() else DDL_POSTGRES
    with get_conn() as conn:
        for stmt in ddl.split(";"):
            s = stmt.strip()
            if s:
                conn.exec_driver_sql(s)

    # Seed COA
    from models_coa import DEFAULT_COA
    with get_conn() as conn:
        count = conn.exec_driver_sql("SELECT COUNT(*) FROM coa").scalar()
        if count == 0:
            for kode, nama, tipe, saldo_normal in DEFAULT_COA:
                conn.exec_driver_sql(
                    "INSERT INTO coa (kode, nama, tipe, saldo_normal) VALUES (:kode,:nama,:tipe,:sn)",
                    {"kode": kode, "nama": nama, "tipe": tipe, "sn": saldo_normal},
                )

# ==================== HELPER ====================
def _ph(sql: str) -> str:
    """Ganti :param jadi placeholder sesuai driver (SQLAlchemy text() sudah handle)."""
    return sql

def fetch_df(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(sql, conn, params=params or {})

def execute(sql: str, params: dict | None = None):
    with get_conn() as conn:
        conn.exec_driver_sql(sql, params or {})

def executemany(sql: str, rows: list[dict]):
    if not rows:
        return
    with get_conn() as conn:
        conn.exec_driver_sql(sql, rows)

# ==================== ID GENERATOR ====================
def next_id_jurnal() -> str:
    df = fetch_df("SELECT id_jurnal FROM jurnal")
    if df.empty:
        return "J001"
    nums = df["id_jurnal"].str.extract(r"(\d+)$")[0].astype(int)
    return f"J{int(nums.max())+1:03d}"

def next_id_trx() -> str:
    df = fetch_df("SELECT id_trx FROM transaksi")
    if df.empty:
        return "T001"
    nums = df["id_trx"].str.extract(r"(\d+)$")[0].astype(int)
    return f"T{int(nums.max())+1:03d}"

def next_id_produk() -> str:
    df = fetch_df("SELECT id_produk FROM produk")
    if df.empty:
        return "P001"
    nums = df["id_produk"].str.extract(r"(\d+)$")[0].astype(int)
    return f"P{int(nums.max())+1:03d}"

# ==================== CRUD: COA ====================
def get_coa() -> pd.DataFrame:
    return fetch_df("SELECT kode, nama, tipe, saldo_normal FROM coa ORDER BY kode")

# ==================== CRUD: PRODUK ====================
def get_produk() -> pd.DataFrame:
    return fetch_df("SELECT id_produk, nama_produk, satuan, harga_beli, harga_jual, stok FROM produk ORDER BY id_produk")

def insert_produk(nama: str, satuan: str, harga_beli: float, harga_jual: float, stok: int) -> str:
    new_id = next_id_produk()
    execute(
        """INSERT INTO produk (id_produk, nama_produk, satuan, harga_beli, harga_jual, stok)
           VALUES (:id, :nama, :sat, :hb, :hj, :stok)""",
        {"id": new_id, "nama": nama, "sat": satuan, "hb": harga_beli, "hj": harga_jual, "stok": stok},
    )
    return new_id

def update_produk(id_produk: str, nama: str, satuan: str, harga_beli: float, harga_jual: float, stok: int):
    execute(
        """UPDATE produk SET nama_produk=:nama, satuan=:sat, harga_beli=:hb,
           harga_jual=:hj, stok=:stok, updated_at=CURRENT_TIMESTAMP
           WHERE id_produk=:id""",
        {"id": id_produk, "nama": nama, "sat": satuan, "hb": harga_beli, "hj": harga_jual, "stok": stok},
    )

def update_stok(id_produk: str, stok_baru: int, harga_beli: float | None = None):
    if harga_beli is None:
        execute("UPDATE produk SET stok=:s, updated_at=CURRENT_TIMESTAMP WHERE id_produk=:id",
                {"s": stok_baru, "id": id_produk})
    else:
        execute("UPDATE produk SET stok=:s, harga_beli=:hb, updated_at=CURRENT_TIMESTAMP WHERE id_produk=:id",
                {"s": stok_baru, "hb": harga_beli, "id": id_produk})

def delete_produk(id_produk: str):
    execute("DELETE FROM produk WHERE id_produk=:id", {"id": id_produk})

# ==================== CRUD: TRANSAKSI ====================
def get_transaksi(tipe: str | None = None) -> pd.DataFrame:
    if tipe:
        return fetch_df(
            "SELECT id_trx, tanggal, tipe, id_produk, nama_produk, qty, harga_satuan, total, pihak AS pelanggan, keterangan "
            "FROM transaksi WHERE tipe=:t ORDER BY tanggal DESC, id_trx DESC",
            {"t": tipe},
        )
    return fetch_df(
        "SELECT id_trx, tanggal, tipe, id_produk, nama_produk, qty, harga_satuan, total, pihak AS pelanggan, keterangan "
        "FROM transaksi ORDER BY tanggal DESC, id_trx DESC"
    )

def insert_transaksi(tipe, tanggal, id_produk, nama_produk, qty, harga_satuan, total, pihak, keterangan) -> str:
    new_id = next_id_trx()
    execute(
        """INSERT INTO transaksi (id_trx, tanggal, tipe, id_produk, nama_produk, qty, harga_satuan, total, pihak, keterangan)
           VALUES (:id, :tgl, :tipe, :idp, :np, :qty, :hs, :tot, :pihak, :ket)""",
        {"id": new_id, "tgl": str(tanggal), "tipe": tipe, "idp": id_produk, "np": nama_produk,
         "qty": qty, "hs": harga_satuan, "tot": total, "pihak": pihak, "ket": keterangan},
    )
    return new_id

# ==================== CRUD: JURNAL ====================
def get_jurnal() -> pd.DataFrame:
    return fetch_df(
        "SELECT id_jurnal, tanggal, kode_akun, nama_akun, debit, kredit, keterangan, ref "
        "FROM jurnal ORDER BY tanggal ASC, id ASC"
    )

def catat_jurnal(entries: list[dict]) -> str:
    """
    entries: [{tanggal, kode_akun, debit, kredit, keterangan, ref}]
    Nama akun di-lookup dari COA.
    """
    coa = get_coa().set_index("kode")
    jid = next_id_jurnal()
    rows = []
    for e in entries:
        kode = e["kode_akun"]
        nama = coa.loc[kode, "nama"] if kode in coa.index else "Unknown"
        rows.append({
            "id_jurnal": jid,
            "tanggal": str(e["tanggal"]),
            "kode_akun": kode,
            "nama_akun": nama,
            "debit": float(e.get("debit", 0)),
            "kredit": float(e.get("kredit", 0)),
            "keterangan": e.get("keterangan", ""),
            "ref": e.get("ref", ""),
        })
    executemany(
        """INSERT INTO jurnal (id_jurnal, tanggal, kode_akun, nama_akun, debit, kredit, keterangan, ref)
           VALUES (:id_jurnal, :tanggal, :kode_akun, :nama_akun, :debit, :kredit, :keterangan, :ref)""",
        rows,
    )
    return jid

# ==================== AGREGASI LAPORAN ====================
def saldo_per_akun() -> pd.DataFrame:
    """Hitung total debit, kredit, dan saldo per akun sesuai saldo_normal."""
    return fetch_df("""
        SELECT c.kode, c.nama, c.tipe, c.saldo_normal,
               COALESCE(SUM(j.debit),0)  AS total_debit,
               COALESCE(SUM(j.kredit),0) AS total_kredit,
               CASE WHEN c.saldo_normal='Debit'
                    THEN COALESCE(SUM(j.debit),0) - COALESCE(SUM(j.kredit),0)
                    ELSE COALESCE(SUM(j.kredit),0) - COALESCE(SUM(j.debit),0)
               END AS saldo
        FROM coa c
        LEFT JOIN jurnal j ON j.kode_akun = c.kode
        GROUP BY c.kode, c.nama, c.tipe, c.saldo_normal
        ORDER BY c.kode
    """)

def total_penjualan() -> float:
    v = fetch_df("SELECT COALESCE(SUM(total),0) AS s FROM transaksi WHERE tipe='JUAL'")["s"].iloc[0]
    return float(v)

def total_pembelian() -> float:
    v = fetch_df("SELECT COALESCE(SUM(total),0) AS s FROM transaksi WHERE tipe='BELI'")["s"].iloc[0]
    return float(v)

def tren_penjualan() -> pd.DataFrame:
    return fetch_df("""
        SELECT tanggal, SUM(total) AS total
        FROM transaksi WHERE tipe='JUAL'
        GROUP BY tanggal ORDER BY tanggal
    """)
