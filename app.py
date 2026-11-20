import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Пульт Качества (Ди-2)", layout="wide")
st.title("Пульт Качества (Ди-2)")

file_path = "data.xlsx"

try:
    # Читаем весь лист БЕЗ заголовков, чтобы найти нужную таблицу
    raw_df = pd.read_excel(file_path, sheet_name="Сводная", header=None)

    # 1. Ищем строку, где начинается таблица по филиалам (ищем слово "Итого" в первом столбце)
    start_row = None
    for i, row in raw_df.iterrows():
        if str(row[0]).strip() == "Итого":
            start_row = i
            break
            
    if start_row is None:
        st.error("Не удалось найти строку 'Итого' в файле. Проверьте файл.")
    else:
        # Берем шапку таблицы (на 1 строку выше "Итого") и две строки данных
        header_row = start_row - 1
        df_branches = raw_df.iloc[start_row : start_row + 3].copy()
        df_branches.columns = raw_df.iloc[header_row].values
        
        # Оставляем только нужные колонки
        cols_to_keep = ['Филиал', 'Все отмены', 'Партн. отмены', 'Неверные', 'Бэдфуд']
        # На всякий случай проверяем, что они есть
        available_cols = [c for c in cols_to_keep if c in df_branches.columns]
        df_branches = df_branches[available_cols]
        
        # Убираем строку "Итого", нам нужны только филиалы
        df_branches = df_branches[df_branches['Филиал'] != 'Итого'].dropna(subset=['Филиал'])

        # Переводим данные в числа
        for col in ['Партн. отмены', 'Неверные', 'Бэдфуд', 'Все отмены']:
            if col in df_branches.columns:
                df_branches[col] = pd.to_numeric(df_branches[col], errors='coerce').fillna(0)

        # --- ОТРИСОВКА ---
        st.subheader("1. Инциденты по филиалам")
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_branches, hide_index=True)
        with col2:
            fig_branch = px.bar(df_branches, x='Филиал', y=['Партн. отмены', 'Неверные', 'Бэдфуд'], 
                                title="Партнерские инциденты", barmode='group',
                                color_discrete_sequence=['#D64545', '#E6A700', '#2E9E4F'])
            st.plotly_chart(fig_branch, use_container_width=True)

        st.divider()

        # 2. Ищем таблицу причин по часам
        st.subheader("2. В какое время и почему происходят инциденты?")
        
        # Ищем строку, где написано "Причины по часам"
        hour_start_row = None
        for i, row in raw_df.iterrows():
            if "Причины по часам" in str(row[0]):
                hour_start_row = i + 3 # Шапка начинается через 3 строки после заголовка
                break
        
        if hour_start_row:
            df_hours = raw_df.iloc[hour_start_row:].copy()
            df_hours.columns = raw_df.iloc[hour_start_row].values
            df_hours = df_hours.dropna(subset=['Час', 'Причина'])
            df_hours = df_hours[['Филиал', 'Час', 'Метрика', 'Причина', 'Случаев']]

            selected_branch = st.selectbox("Выберите точку для детального анализа:", df_hours['Филиал'].unique())
            
            filtered_hours = df_hours[df_hours['Филиал'] == selected_branch]
            
            if not filtered_hours.empty:
                fig_reasons = px.bar(filtered_hours, x='Час', y='Случаев', color='Причина', 
                                     title=f"Причины по часам: {selected_branch}",
                                     labels={'Случаев': 'Количество'})
                st.plotly_chart(fig_reasons, use_container_width=True)
            else:
                st.warning("Нет данных по часам для этой точки.")
        else:
            st.warning("Не удалось найти таблицу 'Причины по часам'.")

except Exception as e:
    st.error(f"Ошибка при чтении файла: {e}")
