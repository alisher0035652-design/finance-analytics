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
st.markdown("Интерактивный дашборд с данными из **Excel-файла** на Google Диске.")

@st.cache_data(ttl=600)
def load_excel_sheets_from_drive():
    creds_dict = None
    
    if "GOOGLE_CREDENTIALS_JSON" in os.environ:
        creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
    elif "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif os.path.exists('credentials.json'):
        with open('credentials.json', 'r', encoding='utf-8') as f:
            creds_dict = json.load(f)
            
    if not creds_dict:
        st.error("❌ Не найдены настройки доступа (секретный ключ).")
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
        # Загружаем все листы файла в виде словаря
        excel_data = pd.read_excel(fh, sheet_name=None)
        return excel_data
    except Exception as e:
        st.error(f"Ошибка при скачивании файла: {e}")
        return None

try:
    sheets_dict = load_excel_sheets_from_drive()
    if sheets_dict:
        # Получаем список всех листов в файле
        sheet_names = list(sheets_dict.keys())
        
        # Создаем выпадающий список для выбора листа в боковой панели или сверху
        st.sidebar.header("📁 Навигация по листам")
        selected_sheet = st.sidebar.selectbox("Выберите нужный лист:", sheet_names)
        
        # Берем датафрейм выбранного листа
        df = sheets_dict[selected_sheet]
        
        st.subheader(f"📋 Лист: {selected_sheet}")
        st.dataframe(df, use_container_width=True)
        
        # Дополнительная аналитика для листов (если есть колонки со статусом или суммой)
        status_col = next((col for col in df.columns if 'СТАТУС' in str(col).upper()), None)
        if status_col:
            st.subheader("📌 Распределение по статусам")
            status_counts = df[status_col].value_counts().reset_index()
            status_counts.columns = ['Статус', 'Количество']
            fig = px.pie(status_counts, names='Статус', values='Количество', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
        sum_col = next((col for col in df.columns if 'СУММА' in str(col).upper()), None)
        if sum_col:
            total_val = pd.to_numeric(df[sum_col], errors='coerce').sum()
            st.metric(label="💰 Общая сумма", value=f"{total_val:,.2f}")
            
except Exception as e:
    st.error(f"Ошибка: {e}")
