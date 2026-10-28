import streamlit as st
import pandas as pd
import io
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="YMM Denetim & KDV-1 Otomasyonu", page_icon="??", layout="wide")

st.title("?? E-Fatura & Muavin Çapraz Denetim Otomasyonu")
st.markdown("XML faturalarınız ile muhasebe muavin dökümünüzü tokuşturun; hataları bulun, cari analizinizi yapın ve KDV-1'i hatasız basın.")
st.markdown("---")

# --- MOCK / TEMEL VERİ İŞLEME FONKSİYONLARI (PANDAS) ---
# Üstat, sen buraya kendi XML okuyucu fonksiyonunu bağlayacaksın. 
# Şimdilik uygulamanın arayüzünü ve denetim motorunu görmen için test verisi üretiyoruz.

def xml_verilerini_getir():
    # Sistemin okuduğu XML verileri (Örnek)
    return pd.DataFrame({
        "Fatura No": ["GIB2026111", "ERS2026222", "FTR2026333", "GIB2026444"],
        "Firma Unvanı": ["ABC Lojistik", "XYZ Kırtasiye", "Demir Hırdavat", "Zirve Temizlik"],
        "VKN": ["1234567890", "0987654321", "1112223334", "9998887776"],
        "XML KDV Haric": [50000, 1200, 8500, 10000],
        "XML KDV Tutari": [10000, 240, 1700, 2000],
        "Tipi": ["Alış", "Alış", "Alış", "Alış"]
    })

def muavin_verilerini_getir():
    # Muhasebeden (Zirve/Luca) çekilen Excel muavin verileri (Örnek)
    return pd.DataFrame({
        "Belge No": ["GIB2026111", "FTR2026333", "GIB2026444", "KAGIT2026555"],
        "Muavin KDV Tutari": [10000, 1700, 200, 500]  # Dikkat: Zirve Temizlik 2000 yerine 200 yazılmış (Hata simülasyonu)
    })

# --- SEKMELER (TABS) ---
sekme_denetim, sekme_cari, sekme_beyanname = st.tabs([
    "?? 1. Çapraz Denetim (XML vs Muavin)", 
    "?? 2. Cari & Gider Analizi", 
    "?? 3. KDV-1 Taslağı"
])

# ==========================================
# 1. SEKME: ÇAPRAZ DENETİM (RECONCILIATION)
# ==========================================
with sekme_denetim:
    col1, col2 = st.columns(2)
    with col1:
        st.file_uploader("?? 1. E-Fatura XML Dosyaları (Zip veya Çoklu)", accept_multiple_files=True)
    with col2:
        st.file_uploader("?? 2. 191/391 veya 120/320 Muavin Excel Dökümü", type=["xlsx", "xls"])
    
    if st.button("? Eşleştir ve Denetim Raporunu Çıkar", type="primary", use_container_width=True):
        with st.spinner("Pandas Motoru: XML ve Muavin satır satır tokuşturuluyor..."):
            time.sleep(1) # Simülasyon
            
            df_xml = xml_verilerini_getir()
            df_muavin = muavin_verilerini_getir()
            
            # PANDAS İLE ÇAPRAZ KONTROL (OUTER JOIN)
            df_denetim = pd.merge(df_xml, df_muavin, left_on="Fatura No", right_on="Belge No", how="outer", indicator=True)
            
            # Hata Durumlarını Sınıflandırma
            def hata_tespit(row):
                if row["_merge"] == "left_only": return "? Muavine İşlenmemiş (Sadece XML'de)"
                elif row["_merge"] == "right_only": return "? XML'de Yok (Manuel İşlenmiş/Kağıt Fatura)"
                elif row["XML KDV Tutari"] != row["Muavin KDV Tutari"]: return "?? Tutar Farkı (Kuruş/Rakam Hatası)"
                else: return "? Kusursuz Eşleşti"
                
            df_denetim["Durum"] = df_denetim.apply(hata_tespit, axis=1)
            
            st.session_state["denetim_sonucu"] = df_denetim
            st.session_state["temiz_xml"] = df_xml # Analizler için
            st.rerun()

    # Rapor Gösterimi
    if "denetim_sonucu" in st.session_state:
        st.markdown("### ?? İSTİSNA VE HATA RAPORU")
        st.info("Sistem milyonlarca satırı taradı ve sadece **sorunlu olan kayıtları** aşağıya döktü.")
        
        # Sadece hataları filtrele
        df_goster = st.session_state["denetim_sonucu"]
        hatalilar = df_goster[df_goster["Durum"] != "? Kusursuz Eşleşti"].copy()
        
        st.dataframe(
            hatalilar[["Fatura No", "Firma Unvanı", "XML KDV Tutari", "Muavin KDV Tutari", "Durum"]], 
            use_container_width=True, hide_index=True
        )

# ==========================================
# 2. SEKME: CARİ VE GİDER ANALİZİ
# ==========================================
with sekme_cari:
    if "temiz_xml" in st.session_state:
        st.markdown("### ?? GİDER VE MALİYET ANALİZİ (En Çok Alım Yapılanlar)")
        df = st.session_state["temiz_xml"]
        
        # PANDAS İLE VKN BAZLI GRUPLAMA VE DİP TOPLAM ALMA
        df_cari = df.groupby(["VKN", "Firma Unvanı"]).agg(
            Fatura_Sayisi=("Fatura No", "count"),
            Toplam_KDV_Haric=("XML KDV Haric", "sum"),
            Toplam_KDV=("XML KDV Tutari", "sum")
        ).reset_index().sort_values(by="Toplam_KDV_Haric", ascending=False)
        
        # Rakamları biçimlendirme
        df_cari["Toplam_KDV_Haric"] = df_cari["Toplam_KDV_Haric"].apply(lambda x: f"{x:,.2f} TL")
        df_cari["Toplam_KDV"] = df_cari["Toplam_KDV"].apply(lambda x: f"{x:,.2f} TL")
        
        st.dataframe(df_cari, use_container_width=True, hide_index=True)
        
        genel_toplam = df["XML KDV Haric"].sum()
        st.success(f"**ALIMLAR GENEL DİP TOPLAM:** {genel_toplam:,.2f} TL")
    else:
        st.warning("Lütfen önce 1. Sekmeden verileri eşleştirin.")

# ==========================================
# 3. SEKME: GİB KDV-1 BEYANNAME TASLAĞI
# ==========================================
with sekme_beyanname:
    st.markdown("### ?? KDV-1 Taslağı (Netleşmiş Verilerle)")
    if "temiz_xml" in st.session_state:
        net_indirilecek = st.session_state["temiz_xml"]["XML KDV Tutari"].sum()
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown("#### ?? İNDİRİMLER (Netleşen Alışlar)")
            st.info(f"**Dönem İndirilecek KDV:** {net_indirilecek:,.2f} TL")
            devreden = st.number_input("Önceki Dönem Devreden KDV", 0.0)
            toplam_indirim = net_indirilecek + devreden
            
        with col_b2:
            st.markdown("#### ?? MATRAH (Netleşen Satışlar)")
            hesaplanan = st.number_input("Hesaplanan KDV (Toplam)", 0.0, step=1000.0)
            
        st.markdown("---")
        fark = hesaplanan - toplam_indirim
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("?? Ödenmesi Gereken KDV", f"{max(0, fark):,.2f} TL")
        with c2:
            st.metric("?? Sonraki Döneme Devreden KDV", f"{max(0, -fark):,.2f} TL")
    else:
        st.warning("Veriler henüz denetlenmedi.")
