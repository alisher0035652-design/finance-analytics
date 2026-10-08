import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="Финансовая аналитика (Excel)", layout="wide")

st.title("📊 Финансовая аналитика компании")
st.markdown("Интерактивный дашборд с данными из **Excel-файла** на Google Диске в реальном времени.")

@st.cache_data(ttl=600) # Кэширование данных на 10 минут
def load_excel_from_drive():
    # Загружаем креды сервисного аккаунта
    creds_dict = None
    if os.path.exists('credentials.json'):
        with open('credentials.json', 'r', encoding='utf-8') as f:
            creds_dict = json.load(f)
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        
    if not creds_dict:
        st.error("❌ Не найден файл `credentials.json` или секреты Streamlit для сервисного аккаунта.")
        return None

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    # ID вашего файла Финансы.xlsx на Google Диске
    file_id = "1vLUdRYxRTp0mb0IakjWXhODRcjYK5YuL"
    
    try:
        # Скачиваем файл в память как байты
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        fh.seek(0)
        # Читаем Excel через pandas с сохранением всех формул и структуры
        df = pd.read_excel(fh)
        return df
    except Exception as e:
        st.error(f"Ошибка при скачивании/чтении Excel-файла с Google Диска: {e}")
        return None

try:
    df = load_excel_from_drive()
    
    if df is not None and not df.empty:
        st.subheader("📋 Данные из Excel-таблицы")
        st.dataframe(df, use_container_width=True)
        
        # Поиск колонки статусов
        status_col = next((col for col in df.columns if 'СТАТУС' in str(col).upper()), None)
        if status_col:
            st.subheader("📌 Распределение по статусам документов")
            status_counts = df[status_col].value_counts().reset_index()
            status_counts.columns = ['Статус', 'Количество']
            fig = px.pie(status_counts, names='Статус', values='Количество', title="Статусы документов", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
        # Поиск колонки суммы
        sum_col = next((col for col in df.columns if 'СУММА' in str(col).upper()), None)
        if sum_col:
            total_val = pd.to_numeric(df[sum_col], errors='coerce').sum()
            st.metric(label="💰 Общая сумма", value=f"{total_val:,.2f}")
    else:
        st.warning("⚠️ Данные не найдены или таблица пуста.")

except Exception as e:
    st.error(f"Детали ошибки: {e}")
