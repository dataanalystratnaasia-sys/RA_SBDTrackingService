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
    def _get(col):
        return str(row[col]).strip() if col in row.index else "-"
    nama      = _get("Nama Pelanggan")
    telp      = _get("No. Telephone")
    alamat    = _get("Alamat")
    merk      = _get("Merk")
    tipe      = _get("Type")
    issue     = _get("Issue")
    guarantee = _get("Guarantee")

    if guarantee.lower() == "ya":
        badge        = "🛡️ <span style='color:#3b76eb;font-weight:600;'>Ya — Barang ini dalam masa garansi</span>"
        badge_bg     = "rgba(59, 118, 235, 0.08)"
        badge_border = "#3b76eb"
    else:
        badge        = "🔧 <span style='color:#f6891f;font-weight:600;'>Tidak — Barang ini di luar masa garansi</span>"
        badge_bg     = "rgba(246, 137, 31, 0.08)"
        badge_border = "#f6891f"

    st.markdown(f"""
    <div class="card">
        <div class="card-title">👤 Informasi Pelanggan</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px 32px;">
            <div>
                <div style="color:#0e508c;font-weight:600;font-size:0.85rem;margin-bottom:4px;">Nama</div>
                <div style="color:#000;margin-bottom:12px;">{nama}</div>
                <div style="color:#0e508c;font-weight:600;font-size:0.85rem;margin-bottom:4px;">No. Telepon</div>
                <div style="color:#000;margin-bottom:12px;">{telp}</div>
                <div style="color:#0e508c;font-weight:600;font-size:0.85rem;margin-bottom:4px;">Alamat</div>
                <div style="color:#000;">{alamat}</div>
            </div>
            <div>
                <div style="color:#0e508c;font-weight:600;font-size:0.85rem;margin-bottom:4px;">Merk</div>
                <div style="color:#000;margin-bottom:12px;">{merk}</div>
                <div style="color:#0e508c;font-weight:600;font-size:0.85rem;margin-bottom:4px;">Type</div>
                <div style="color:#000;margin-bottom:12px;">{tipe}</div>
                <div style="color:#0e508c;font-weight:600;font-size:0.85rem;margin-bottom:4px;">Keluhan / Issue</div>
                <div style="color:#000;">{issue}</div>
            </div>
        </div>
        <div style="margin-top:16px; padding:12px 16px; background:{badge_bg}; border-left:4px solid {badge_border}; border-radius:8px;">
            <b>Garansi:</b> {badge}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_progress(row):
    selesai = 0
    total   = len(SERVICE_COLS)
    status_list = []

    for col in SERVICE_COLS:
        if col in row.index:
            val = row[col]
            if isinstance(val, bool):
                done = val
            else:
                done = str(val).strip().upper() in ("TRUE", "1", "YA", "YES")
        else:
            done = False
        if done:
            selesai += 1
        status_list.append((col, done))

    persen = int((selesai / total) * 100) if total > 0 else 0

    timeline_items = ""
    for i, (nama, done) in enumerate(status_list):
        is_last  = (i == len(status_list) - 1)
        line_div = "" if is_last else '<div class="line"></div>'
        dot_cls   = "dot done"   if done else "dot pending"
        label_cls = "label-done" if done else "label-pending"
        desc      = "Selesai"    if done else "Menunggu"
        desc_cls  = "desc-done"  if done else "desc-pending"

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
        </div>"""

    # Catatan teknisi
    catatan = str(row["Catatan Service"]).strip() if "Catatan Service" in row.index else ""
    catatan_content = catatan if catatan and catatan.upper() not in ("", "NONE", "NAN") else None
    catatan_html = f"""
    <div class="card-catatan">
        <div class="card-title">🗒️ Catatan Teknisi</div>
        <div style="color:{'#000' if catatan_content else '#aaa'}; font-size:0.97rem;">
            {catatan_content if catatan_content else "Belum ada catatan dari teknisi."}
        </div>
    </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: transparent;
        overflow: hidden;
    }}
    .card {{
        background: #f5f8ff;
        border: 1px solid #d0dff5;
        border-radius: 12px;
        padding: 24px 28px;
        box-shadow: 0 2px 8px rgba(14,80,140,0.08);
        margin-bottom: 12px;
    }}
    .card-catatan {{
        background: #f5f8ff;
        border: 1px solid #d0dff5;
        border-radius: 12px;
        padding: 24px 28px;
        box-shadow: 0 2px 8px rgba(14,80,140,0.08);
    }}
    .card-title {{
        color: #0e508c; font-size: 1.15rem; font-weight: 700;
        margin-bottom: 8px;
    }}
    .progress-label {{
        color: #0e508c; font-size: 0.88rem;
        margin-bottom: 6px; font-weight: 600;
    }}
    .progress-wrap {{
        background: #e0e8f5; border-radius: 8px;
        height: 10px; margin-bottom: 20px; overflow: hidden;
    }}
    .progress-fill {{
        height: 100%; width: {persen}%;
        background: #f6891f; border-radius: 8px;
        transition: width 0.4s ease;
    }}
    .timeline {{ padding: 4px 0 4px 0; }}
    .item {{ display: flex; align-items: flex-start; gap: 14px; }}
    .col-left {{
        display: flex; flex-direction: column;
        align-items: center; width: 18px; flex-shrink: 0;
    }}
    .dot {{
        width: 14px; height: 14px;
        border-radius: 50%; margin-top: 4px; flex-shrink: 0;
    }}
    .dot.done    {{ background-color: #f6891f; }}
    .dot.pending {{ background-color: #fff; border: 2px solid #3b76eb; }}
    .line {{
        width: 2px; min-height: 28px; flex: 1;
        background-color: #d0dff5; margin: 3px 0;
    }}
    .col-right {{ padding-bottom: 16px; }}
    .label-done    {{ font-weight: 600; color: #000; font-size: 0.95rem; }}
    .label-pending {{ font-weight: 400; color: #888; font-size: 0.95rem; }}
    .desc-done     {{ color: #f6891f; font-size: 0.82rem; margin-top: 2px; font-weight: 600; }}
    .desc-pending  {{ color: #aaa;    font-size: 0.82rem; margin-top: 2px; }}
</style>
</head>
<body>
<div id="content">
    <div class="card">
        <div class="card-title">📊 Progress Servis</div>
        <div class="progress-label">{persen}% ({selesai}/{total} selesai)</div>
        <div class="progress-wrap"><div class="progress-fill"></div></div>
        <div class="timeline">{timeline_items}</div>
    </div>
    {catatan_html}
</div>
<script>
    function sendHeight() {{
        const h = document.getElementById('content').scrollHeight;
        window.parent.postMessage({{
            type: 'streamlit:setFrameHeight',
            height: h + 8
        }}, '*');
    }}
    window.addEventListener('load', sendHeight);
    window.addEventListener('resize', sendHeight);
    const ro = new ResizeObserver(sendHeight);
    ro.observe(document.getElementById('content'));
</script>
</body>
</html>"""

    components.html(html, height=total * 68 + 280, scrolling=False)


# ─────────────────────────────────────────────
# UI UTAMA
# ─────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Tracking Servis",
        page_icon="🔧",
        layout="centered",
    )

    st.markdown("""
    <style>
        .stApp { background-color: #ffffff; }
        .stApp, .stApp p, .stApp div, .stApp span { color: #000000; }
        h1, h2, h3 { color: #0e508c !important; }
        strong { color: #0e508c; }

        .card {
            background-color: #f5f8ff;
            border: 1px solid #d0dff5;
            border-radius: 12px;
            padding: 24px 28px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(14, 80, 140, 0.08);
        }
        .card-title {
            color: #0e508c;
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 16px;
        }

        .stTextInput > div > div > input {
            background-color: #f5f8ff;
            color: #000000;
            border: 1.5px solid #3b76eb;
            border-radius: 8px;
        }
        .stTextInput > div > div > input::placeholder { color: #aaaaaa; }
        .stTextInput > div > div > input:focus {
            border-color: #0e508c;
            box-shadow: 0 0 0 2px #52a2ff44;
        }

        .stButton > button {
            background-color: #f6891f !important;
            color: #ffffff !important;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            transition: background 0.2s;
        }
        .stButton > button:hover { background-color: #faa849 !important; }

        .stProgress > div > div > div > div { background-color: #f6891f; }
        .stProgress > div > div > div { background-color: #e8eef8; border-radius: 8px; }

        .stAlert {
            background-color: #eaf3ff !important;
            border-left: 4px solid #52a2ff !important;
            color: #0e508c !important;
            border-radius: 8px;
        }
        .stSuccess {
            background-color: #eaf3ff !important;
            border-left: 4px solid #3b76eb !important;
            color: #0e508c !important;
        }
        .stWarning {
            background-color: rgba(246,137,31,0.08) !important;
            border-left: 4px solid #faa849 !important;
            color: #000 !important;
        }
        .stError { border-left: 4px solid #f6891f !important; }
        .stCaption { color: #888888 !important; }
        hr { border-color: #e0e8f5; }
        footer p { color: #aaaaaa !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <h1 style='text-align:center; font-size:2.2rem;'>🔧 Tracking Servis Barang</h1>
        <p style='text-align:center; color:gray;'>Masukkan ID servis kamu untuk melihat progress servis.</p>
        <hr>
    """, unsafe_allow_html=True)

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
