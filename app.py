import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="Финансовая аналитика", layout="wide")

st.title("📊 Финансовая аналитика компании")
st.markdown("Интерактивный дашборд: **Cash-flow** и **Анализ Дт-Кт**.")

@st.cache_data(ttl=600)
def load_excel_bytes_from_drive():
    creds_dict = None
    if "GOOGLE_CREDENTIALS_JSON" in os.environ:
        creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif os.path.exists('credentials.json'):
        with open('credentials.json', 'r', encoding='utf-8') as f:
            creds_dict = json.load(f)
            
    if not creds_dict:
        return None

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    file_id = "1vLUdRYxRTp0mb0IakjWXhODRcjYK5YuL"
    
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh
    except Exception as e:
        st.error(f"Ошибка при скачивании файла: {e}")
        return None

fh = load_excel_bytes_from_drive()

if fh:
    try:
        # Читаем все листы
        xls = pd.ExcelFile(fh)
        sheet_names = xls.sheet_names
        
        # Находим нужные листы по именам
        dt_kt_sheet = next((s for s in sheet_names if 'дт' in s.lower() or 'кт' in s.lower() or 'анализ' in s.lower()), sheet_names[0])
        cash_sheet = next((s for s in sheet_names if 'cash' in s.lower() or 'flow' in s.lower()), sheet_names[1] if len(sheet_names) > 1 else sheet_names[0])
        
        tabs = st.tabs(["📌 Анализ Дт-Кт", "💵 Cash-flow"])
        
        # --- Вкладка 1: Анализ Дт-Кт ---
        with tabs[0]:
            st.subheader("📋 Анализ Дт-Кт по контрагентам")
            
            # Читаем весь лист без заголовков, чтобы точно вытащить диапазон I1:J7 (колонки 8 и 9 в индексах Python)
            raw_df = pd.read_excel(xls, sheet_name=dt_kt_sheet, header=None)
            
            # 1. Верхняя таблица (диапазон I1:J7 -> строки 0-6, столбцы 8-9)
            if raw_df.shape[1] >= 10 and raw_df.shape[0] >= 7:
                # Извлекаем блок I1:J7
                summary_block = raw_df.iloc[0:7, 8:10].copy()
                summary_block.columns = ['Показатель', 'Значение']
                
                # Если у нас несколько контрагентов или таблица позволяет выбрать, сделаем красивый вид
                st.markdown("### Сводка по контрагенту")
                
                # Отображаем в виде аккуратных метрик или таблицы
                col1, col2 = st.columns([1, 2])
                with col1:
                    for idx, row in summary_block.iterrows():
                        st.text(f"{row['Показатель']}:")
                with col2:
                    for idx, row in summary_block.iterrows():
                        st.markdown(f"**{row['Значение']}**")
            
            st.markdown("---")
            
            # 2. Нижняя общая таблица (начиная со строки 9, где строка 9 — заголовки, индексы с 8)
            main_df = pd.read_excel(xls, sheet_name=dt_kt_sheet, skiprows=8)
            # Очистим пустые строки/колонки если они есть
            main_df = main_df.dropna(how='all')
            
            st.markdown("### Общая таблица данных (срок/транзакции)")
            st.dataframe(main_df, use_container_width=True)
            
        # --- Вкладка 2: Cash-flow ---
        with tabs[1]:
            st.subheader("💵 Cash-flow")
            cash_df = pd.read_excel(xls, sheet_name=cash_sheet)
            st.dataframe(cash_df, use_container_width=True)
            
    except Exception as e:
        st.error(f"Ошибка при обработке структуры Excel: {e}")
else:
    st.warning("⚠️ Не удалось загрузить файл с Google Диска.")
