import streamlit as st
import pandas as pd
import time
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="VAT Audit & KDV-1 Automation", page_icon="⚖️", layout="wide")

# ==========================================
# 1. DİL SÖZLÜĞÜ (i18n TRANSLATIONS)
# ==========================================
lang_dict = {
    "TR": {
        "sidebar_title": "🌍 Dil / Language",
        "main_title": "⚖️ E-Fatura & Muavin Çapraz Denetim Otomasyonu",
        "sub_title": "XML faturalarınız ile muhasebe muavin dökümünüzü tokuşturun; hataları bulun ve KDV-1'i hatasız basın.",
        "tab1": "🔍 1. Çapraz Denetim",
        "tab2": "🏢 2. Cari & Gider Analizi",
        "tab3": "📊 3. KDV-1 Taslağı",
        "upload_xml": "📥 1. E-Fatura XML Dosyaları (Zip veya Çoklu)",
        "upload_ledger": "📥 2. 191/391 veya 120/320 Muavin Excel Dökümü",
        "btn_run": "⚡ Eşleştir ve Denetim Raporunu Çıkar",
        "btn_reset": "🗑️ Tüm Verileri ve Tabloları Sıfırla",
        "msg_processing": "Pandas Motoru: Veriler satır satır tokuşturuluyor...",
        "status_perfect": "✅ Kusursuz Eşleşti",
        "status_miss_ledger": "❌ Muavine İşlenmemiş",
        "status_miss_xml": "❌ XML'de Yok (Manuel/Kağıt)",
        "status_diff": "⚠️ Tutar Farkı",
        "report_title": "🚨 İSTİSNA VE HATA RAPORU",
        "report_desc": "Sistem sadece sorunlu olan kayıtları aşağıya döktü.",
        "excel_title": "📦 Kalem Bazlı Detay Raporu (Mal/Hizmet İçerikleri)",
        "excel_btn": "📥 Alış Faturaları Detay Listesini İndir (.xlsx)",
        "analysis_title": "📉 GİDER VE MALİYET ANALİZİ (En Çok Alım Yapılanlar)",
        "analysis_total": "ALIMLAR GENEL DİP TOPLAM",
        "vat_title": "📊 KDV-1 Taslağı (Netleşmiş Verilerle)",
        "vat_deductions": "#### 📥 İNDİRİMLER (Netleşen Alışlar)",
        "vat_period": "Dönem İndirilecek KDV:",
        "vat_prev": "Önceki Dönem Devreden KDV",
        "vat_base": "#### 📤 MATRAH (Netleşen Satışlar)",
        "vat_calc": "Hesaplanan KDV (Toplam)",
        "vat_payable": "💰 Ödenmesi Gereken KDV",
        "vat_forward": "🔄 Sonraki Döneme Devreden KDV",
        "warn_no_data": "Lütfen önce 1. Sekmeden verileri eşleştirin."
    },
    "EN": {
        "sidebar_title": "🌍 Language / Dil",
        "main_title": "⚖️ E-Invoice & Ledger Cross-Audit Automation",
        "sub_title": "Cross-check your XML invoices against accounting ledger records; find anomalies and generate VAT returns.",
        "tab1": "🔍 1. Cross-Audit",
        "tab2": "🏢 2. Vendor Analysis",
        "tab3": "📊 3. VAT Return Draft",
        "upload_xml": "📥 1. E-Invoice XML Files (Zip/Multiple)",
        "upload_ledger": "📥 2. General Ledger (Excel)",
        "btn_run": "⚡ Run Matching & Generate Audit Report",
        "btn_reset": "🗑️ Reset All Data and Tables",
        "msg_processing": "Pandas Engine: Reconciling data row by row...",
        "status_perfect": "✅ Perfect Match",
        "status_miss_ledger": "❌ Missing in Ledger",
        "status_miss_xml": "❌ Missing in XML (Manual/Paper)",
        "status_diff": "⚠️ Amount Mismatch",
        "report_title": "🚨 EXCEPTION & ANOMALY REPORT",
        "report_desc": "The system filtered the data and only displays problematic records below.",
        "excel_title": "📦 Itemized Detail Report (Goods/Services)",
        "excel_btn": "📥 Download Purchase Invoices Detail List (.xlsx)",
        "analysis_title": "📉 VENDOR & EXPENSE ANALYSIS (Top Suppliers)",
        "analysis_total": "PURCHASES GRAND TOTAL",
        "vat_title": "📊 VAT Return Draft (Reconciled Data)",
        "vat_deductions": "#### 📥 DEDUCTIONS (Reconciled Purchases)",
        "vat_period": "Current Period Deductible VAT:",
        "vat_prev": "Previous Period VAT Carried Forward",
        "vat_base": "#### 📤 BASE (Reconciled Sales)",
        "vat_calc": "Calculated VAT (Total)",
        "vat_payable": "💰 Payable VAT",
        "vat_forward": "🔄 VAT Carried Forward",
        "warn_no_data": "Please run the matching process in Tab 1 first."
    }
}

# --- DİL SEÇİMİ (SIDEBAR) ---
st.sidebar.title(lang_dict["TR"]["sidebar_title"])
selected_lang = st.sidebar.radio("", ["TR", "EN"])
T = lang_dict[selected_lang] # Seçilen dil paketini T değişkenine atadık

# --- RESET MEKANİZMASI ---
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

if st.sidebar.button(T["btn_reset"]):
    for key in ["temiz_xml", "denetim_sonucu"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state["uploader_key"] += 1
    st.rerun()

# --- MOCK VERİ FONKSİYONLARI ---
def xml_verilerini_getir():
    return pd.DataFrame({
        "Fatura No": ["GIB2026111", "ERS2026222", "FTR2026333", "GIB2026444"],
        "Firma Unvanı": ["ABC Lojistik", "XYZ Kırtasiye", "Demir Hırdavat", "Zirve Temizlik"],
        "VKN": ["1234567890", "0987654321", "1112223334", "9998887776"],
        "Mal/Hizmet Cinsi": ["Nakliye Hizmeti", "Kırtasiye Malzemesi", "Hırdavat Aksamı", "Temizlik Malzemesi"],
        "XML KDV Haric": [50000, 1200, 8500, 10000],
        "XML KDV Tutari": [10000, 240, 1700, 2000]
    })

def muavin_verilerini_getir():
    return pd.DataFrame({
        "Belge No": ["GIB2026111", "FTR2026333", "GIB2026444", "KAGIT2026555"],
        "Muavin KDV Tutari": [10000, 1700, 200, 500] 
    })

# --- ANA EKRAN ---
st.title(T["main_title"])
st.markdown(T["sub_title"])
st.markdown("---")

sekme_denetim, sekme_cari, sekme_beyanname = st.tabs([T["tab1"], T["tab2"], T["tab3"]])

# ==========================================
# 1. SEKME: ÇAPRAZ DENETİM & EXCEL İNDİRME
# ==========================================
with sekme_denetim:
    col1, col2 = st.columns(2)
    with col1:
        st.file_uploader(T["upload_xml"], accept_multiple_files=True, key=f"xml_{st.session_state['uploader_key']}")
    with col2:
        st.file_uploader(T["upload_ledger"], type=["xlsx", "xls"], key=f"excel_{st.session_state['uploader_key']}")
    
    if st.button(T["btn_run"], type="primary", use_container_width=True):
        with st.spinner(T["msg_processing"]):
            time.sleep(1) # İşlem simülasyonu
            
            df_xml = xml_verilerini_getir()
            df_muavin = muavin_verilerini_getir()
            
            df_denetim = pd.merge(df_xml, df_muavin, left_on="Fatura No", right_on="Belge No", how="outer", indicator=True)
            
            def hata_tespit(row):
                if row["_merge"] == "left_only": return T["status_miss_ledger"]
                elif row["_merge"] == "right_only": return T["status_miss_xml"]
                elif row["XML KDV Tutari"] != row["Muavin KDV Tutari"]: return T["status_diff"]
                else: return T["status_perfect"]
                
            df_denetim["Durum / Status"] = df_denetim.apply(hata_tespit, axis=1)
            
            st.session_state["denetim_sonucu"] = df_denetim
            st.session_state["temiz_xml"] = df_xml
            st.rerun()

    if "denetim_sonucu" in st.session_state:
        st.markdown(f"### {T['report_title']}")
        st.info(T["report_desc"])
        
        df_goster = st.session_state["denetim_sonucu"]
        hatalilar = df_goster[df_goster["Durum / Status"] != T["status_perfect"]]
        
        st.dataframe(
            hatalilar[["Fatura No", "Firma Unvanı", "XML KDV Tutari", "Muavin KDV Tutari", "Durum / Status"]], 
            use_container_width=True, hide_index=True
        )
        
        # --- EXCEL İNDİRME BÖLÜMÜ ---
        st.markdown("---")
        st.markdown(f"### {T['excel_title']}")
        
        def excel_olustur(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Fatura_Detaylari')
                worksheet = writer.sheets['Fatura_Detaylari']
                for i, col in enumerate(df.columns):
                    column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, column_len)
            return output.getvalue()

        excel_dosyasi = excel_olustur(st.session_state["temiz_xml"])
        
        st.download_button(
            label=T["excel_btn"],
            data=excel_dosyasi,
            file_name="Alis_Faturalari_Kalem_Detaylari.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

# ==========================================
# 2. SEKME: CARİ VE GİDER ANALİZİ
# ==========================================
with sekme_cari:
    if "temiz_xml" in st.session_state:
        st.markdown(f"### {T['analysis_title']}")
        df = st.session_state["temiz_xml"]
        
        df_cari = df.groupby(["VKN", "Firma Unvanı"]).agg(
            Fatura_Sayisi=("Fatura No", "count"),
            Toplam_KDV_Haric=("XML KDV Haric", "sum"),
            Toplam_KDV=("XML KDV Tutari", "sum")
        ).reset_index().sort_values(by="Toplam_KDV_Haric", ascending=False)
        
        st.dataframe(df_cari, use_container_width=True, hide_index=True)
        genel_toplam = df["XML KDV Haric"].sum()
        st.success(f"**{T['analysis_total']}:** {genel_toplam:,.2f}")
    else:
        st.warning(T["warn_no_data"])

# ==========================================
# 3. SEKME: KDV-1 TASLAĞI
# ==========================================
with sekme_beyanname:
    st.markdown(f"### {T['vat_title']}")
    if "temiz_xml" in st.session_state:
        net_indirilecek = st.session_state["temiz_xml"]["XML KDV Tutari"].sum()
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown(T["vat_deductions"])
            st.info(f"**{T['vat_period']}** {net_indirilecek:,.2f}")
            devreden = st.number_input(T["vat_prev"], 0.0)
            toplam_indirim = net_indirilecek + devreden
            
        with col_b2:
            st.markdown(T["vat_base"])
            hesaplanan = st.number_input(T["vat_calc"], 0.0, step=1000.0)
            
        st.markdown("---")
        fark = hesaplanan - toplam_indirim
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric(T["vat_payable"], f"{max(0, fark):,.2f}")
        with c2:
            st.metric(T["vat_forward"], f"{max(0, -fark):,.2f}")
    else:
        st.warning(T["warn_no_data"])
