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
        xls = pd.ExcelFile(fh)
        sheet_names = xls.sheet_names
        
        dt_kt_sheet = next((s for s in sheet_names if 'дт' in s.lower() or 'кт' in s.lower() or 'анализ' in s.lower()), sheet_names[0])
        cash_sheet = next((s for s in sheet_names if 'cash' in s.lower() or 'flow' in s.lower()), sheet_names[1] if len(sheet_names) > 1 else sheet_names[0])
        
        tabs = st.tabs(["📌 Анализ Дт-Кт", "💵 Cash-flow"])
        
        # --- Вкладка 1: Анализ Дт-Кт ---
        with tabs[0]:
            st.subheader("📋 Анализ Дт-Кт по контрагентам")
            
            # Читаем нижнюю общую таблицу (начиная со строки 9)
            main_df = pd.read_excel(xls, sheet_name=dt_kt_sheet, skiprows=8)
            main_df = main_df.dropna(how='all')
            
            # Убираем лишние колонки, у которых названия начинаются с "Unnamed" или пустые
            valid_columns = [col for col in main_df.columns if str(col).strip() and not str(col).startswith('Unnamed')]
            main_df = main_df[valid_columns]
            
            # Функция для форматирования чисел с разделителями тысяч
            def format_number(val):
                try:
                    num = float(val)
                    return f"{num:,.2f}"
                except:
                    return str(val)
            
            contragent_col = next((col for col in main_df.columns if 'КОНТРАГЕНТ' in str(col).upper()), main_df.columns[1] if len(main_df.columns) > 1 else None)
            inn_col = next((col for col in main_df.columns if 'ИНН' in str(col).upper()), main_df.columns[0] if len(main_df.columns) > 0 else None)
            
            if contragent_col:
                unique_contragents = sorted(main_df[contragent_col].dropna().astype(str).unique().tolist())
                
                selected_contragent = st.selectbox(
                    "🔍 Поиск и выбор контрагента (начните вводить название):",
                    options=unique_contragents
                )
                
                if selected_contragent:
                    filtered_row = main_df[main_df[contragent_col].astype(str) == selected_contragent]
                    
                    if not filtered_row.empty:
                        row_data = filtered_row.iloc[0]
                        
                        inn_val = row_data[inn_col] if inn_col in main_df.columns else "—"
                        postuplenie = format_number(row_data['Поступление']) if 'Поступление' in main_df.columns else "0.00"
                        spisanie = format_number(row_data['Списание']) if 'Списание' in main_df.columns else "0.00"
                        vkhodyashchie = format_number(row_data['Входящие']) if 'Входящие' in main_df.columns else "0.00"
                        iskhodyashchie = format_number(row_data['Исходящие']) if 'Исходящие' in main_df.columns else "0.00"
                        saldo = format_number(row_data['Сальдо']) if 'Сальдо' in main_df.columns else "0.00"
                        
                        st.markdown("### Сводка по контрагенту")
                        
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.text("ИНН:")
                            st.text("Контрагент:")
                            st.text("Поступление:")
                            st.text("Списание:")
                            st.text("Входящие:")
                            st.text("Исходящие:")
                            st.text("Сальдо:")
                        with col2:
                            st.markdown(f"**{inn_val}**")
                            st.markdown(f"**{selected_contragent}**")
                            st.markdown(f"**{postuplenie}**")
                            st.markdown(f"**{spisanie}**")
                            st.markdown(f"**{vkhodyashchie}**")
                            st.markdown(f"**{iskhodyashchie}**")
                            st.markdown(f"<span style='color:red; font-weight:bold;'>{saldo}</span>", unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### Общая таблица данных (срок/транзакции)")
            
            # Также отформатируем числовые колонки в общей таблице для удобства чтения
            display_df = main_df.copy()
            for col in display_df.columns:
                if any(k in str(col).lower() for k in ['сумма', 'поступление', 'списание', 'входящие', 'исходящие', 'сальдо']):
                    display_df[col] = pd.to_numeric(display_df[col], errors='coerce').apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

            st.dataframe(display_df, use_container_width=True)
            
        # --- Вкладка 2: Cash-flow ---
        with tabs[1]:
            st.subheader("💵 Cash-flow")
            cash_df = pd.read_excel(xls, sheet_name=cash_sheet)
            # Уберем мусорные колонки и здесь тоже
            cash_df = cash_df.dropna(how='all')
            valid_cash_cols = [col for col in cash_df.columns if str(col).strip() and not str(col).startswith('Unnamed')]
            cash_df = cash_df[valid_cash_cols]
            st.dataframe(cash_df, use_container_width=True)
            
    except Exception as e:
        st.error(f"Ошибка при обработке структуры Excel: {e}")
else:
    st.warning("⚠️ Не удалось загрузить файл с Google Диска.")
