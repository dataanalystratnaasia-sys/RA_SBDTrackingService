import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ─────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────
SPREADSHEET_ID = "16oEcvCWuhM_FPl62IiwNQBX90NBYEkNQszQljNe7YCA"
SHEET_NAME = "TRACKING"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Kolom progress servis (indeks 7–17, setelah kolom info pelanggan)
SERVICE_COLS = [
    "Barang Diterima RA",
    "Waiting List",
    "Status Pengecekan Teknisi",
    "Pengajuan Service ke Customer",
    "Persetujuan Perbaikan Customer",
    "Proses Inden Part",
    "Progress Perbaikan Barang",
    "Status Uji Coba Barang",
    "Status Selesai Perbaikan",
    "Status Pengiriman Barang",
    "Status Barang Diterima Customer",
]

# ─────────────────────────────────────────────
# KONEKSI KE GOOGLE SHEET
# ─────────────────────────────────────────────
@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=60)
def load_data():
    client = get_gsheet_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.worksheet(SHEET_NAME)
    all_values = sheet.get_all_values()

    if len(all_values) < 2:
        return pd.DataFrame()

    headers = all_values[0]
    rows    = all_values[1:]

    df = pd.DataFrame(rows, columns=headers)
    df = df[df.iloc[:, 0].str.strip() != ""]
    return df


# ─────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────
def cari_barang(df, id_barang):
    id_bersih = id_barang.strip().upper()
    mask = df.iloc[:, 0].str.strip().str.upper() == id_bersih
    hasil = df[mask]
    return hasil.iloc[0] if not hasil.empty else None


def render_info_pelanggan(row):
    """Tampilkan kartu info pelanggan."""
    def _get(col):
        return str(row[col]).strip() if col in row.index else "-"
    nama   = _get("Nama Pelanggan")
    telp   = _get("No. Telephone")
    alamat = _get("Alamat")
    merk   = _get("Merk")
    tipe   = _get("Type")
    issue  = _get("Issue")

    st.markdown("### 👤 Informasi Pelanggan")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Nama**")
        st.write(nama)
        st.markdown(f"**No. Telepon**")
        st.write(telp)
        st.markdown(f"**Alamat**")
        st.write(alamat)
    with col2:
        st.markdown(f"**Merk**")
        st.write(merk)
        st.markdown(f"**Type**")
        st.write(tipe)
        st.markdown(f"**Keluhan / Issue**")
        st.write(issue)

    st.markdown("---")


def render_progress(row):
    selesai = 0
    total   = len(SERVICE_COLS)

    status_list = []
    for col in SERVICE_COLS:
        val = str(row[col]).strip().upper() if col in row.index else "FALSE"
        done = val == "TRUE"
        if done:
            selesai += 1
        status_list.append((col, done))

    persen = int((selesai / total) * 100) if total > 0 else 0

    st.markdown(f"### 📊 Progress Servis: {persen}% ({selesai}/{total} selesai)")
    st.progress(persen / 100)
    st.markdown("")

    # Bangun HTML timeline
    timeline_items = ""
    for i, (nama, done) in enumerate(status_list):
        is_last  = (i == len(status_list) - 1)
        line_div = "" if is_last else '<div class="line"></div>'

        if done:
            dot_cls   = "dot done"
            label_cls = "label-done"
            desc      = "Selesai"
            desc_cls  = "desc-done"
        else:
            dot_cls   = "dot pending"
            label_cls = "label-pending"
            desc      = "Menunggu"
            desc_cls  = "desc-pending"

        timeline_items += f"""
        <div class="item">
            <div class="col-left">
                <div class="{dot_cls}"></div>
                {line_div}
            </div>
            <div class="col-right">
                <div class="{label_cls}">{nama}</div>
                <div class="{desc_cls}">{desc}</div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
    body {{
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: transparent;
    }}
    .timeline {{ padding: 4px 0 8px 0; }}
    .item {{
        display: flex;
        align-items: flex-start;
        gap: 14px;
    }}
    .col-left {{
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 18px;
        flex-shrink: 0;
    }}
    .dot {{
        width: 14px;
        height: 14px;
        border-radius: 50%;
        margin-top: 4px;
        flex-shrink: 0;
    }}
    .dot.done    {{ background-color: #1DB954; }}
    .dot.pending {{ background-color: #ffffff; border: 2px solid #888; box-sizing: border-box; }}
    .line {{
        width: 2px;
        min-height: 30px;
        flex: 1;
        background-color: #444;
        margin: 3px 0;
    }}
    .col-right {{ padding-bottom: 18px; }}
    .label-done    {{ font-weight: 600; color: #f0f0f0; font-size: 0.97rem; }}
    .label-pending {{ font-weight: 400; color: #888;    font-size: 0.97rem; }}
    .desc-done    {{ color: #1DB954; font-size: 0.82rem; margin-top: 2px; }}
    .desc-pending {{ color: #666;    font-size: 0.82rem; margin-top: 2px; }}
</style>
</head>
<body>
    <div class="timeline">
        {timeline_items}
    </div>
</body>
</html>"""

    tinggi = total * 58 + 20
    components.html(html, height=tinggi, scrolling=False)

    # Catatan teknisi (kolom "Catatan Service")
    st.markdown("---")
    catatan = str(row["Catatan Service"]).strip() if "Catatan Service" in row.index else ""

    st.markdown("### 🗒️ Catatan Teknisi")
    if catatan and catatan.upper() not in ("", "NONE", "NAN"):
        st.info(catatan)
    else:
        st.caption("Belum ada catatan dari teknisi.")


# ─────────────────────────────────────────────
# UI UTAMA
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Tracking Servis",
        page_icon="🔧",
        layout="centered",
    )

    st.markdown(
        """
        <h1 style='text-align:center; font-size:2.2rem;'>🔧 Tracking Servis Barang</h1>
        <p style='text-align:center; color:gray;'>Masukkan ID servis kamu untuk melihat progress servis.</p>
        <hr>
        """,
        unsafe_allow_html=True,
    )

    id_input = st.text_input(
        "ID Servis",
        placeholder="Contoh: 164/SC-SBD/05/26",
        max_chars=50,
    )

    cari = st.button("🔍 Cek Status", use_container_width=True, type="primary")

    if cari or id_input:
        if not id_input.strip():
            st.warning("Silakan masukkan ID servis terlebih dahulu.")
            return

        with st.spinner("Mengambil data..."):
            try:
                df = load_data()
            except Exception as e:
                st.error(f"❌ Gagal terhubung ke database: {e}")
                return

        if df.empty:
            st.error("❌ Tidak ada data di sheet. Hubungi admin.")
            return

        row = cari_barang(df, id_input)

        if row is None:
            st.error(f"❌ ID **{id_input.strip()}** tidak ditemukan. Periksa kembali ID servis kamu.")
        else:
            st.success(f"✅ Data ditemukan untuk ID: **{row.iloc[0]}**")
            st.markdown("---")
            render_info_pelanggan(row)
            render_progress(row)

    st.markdown(
        "<br><hr><p style='text-align:center; color:lightgray; font-size:0.8rem;'>Powered by Streamlit & Google Sheets</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()