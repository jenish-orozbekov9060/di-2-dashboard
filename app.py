import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Пульт Качества (Ди-2)", layout="wide")
st.title("Пульт Качества (Ди-2)")

file_path = "data.xlsx"

try:
    # Читаем весь лист БЕЗ заголовков
    raw_df = pd.read_excel(file_path, sheet_name="Сводная", header=None)

    # ============================================================
    # БЛОК 1: ИНЦИДЕНТЫ ПО ФИЛИАЛАМ (Работает)
    # ============================================================
    start_row = None
    for i, row in raw_df.iterrows():
        if str(row[0]).strip() == "Итого":
            start_row = i
            break
            
    if start_row is not None:
        header_row = start_row - 1
        df_branches = raw_df.iloc[start_row : start_row + 3].copy()
        df_branches.columns = raw_df.iloc[header_row].values
        
        cols_to_keep = ['Филиал', 'Все отмены', 'Партн. отмены', 'Неверные', 'Бэдфуд']
        available_cols = [c for c in cols_to_keep if c in df_branches.columns]
        df_branches = df_branches[available_cols]
        df_branches = df_branches[df_branches['Филиал'] != 'Итого'].dropna(subset=['Филиал'])

        for col in ['Партн. отмены', 'Неверные', 'Бэдфуд', 'Все отмены']:
            if col in df_branches.columns:
                df_branches[col] = pd.to_numeric(df_branches[col], errors='coerce').fillna(0)

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

        # ============================================================
        # БЛОК 2: ПРИЧИНЫ ПО ЧАСАМ (Исправленный)
        # ============================================================
        st.subheader("2. В какое время и почему происходят инциденты?")
        
        # В вашем Excel-файле детальная таблица по часам начинается на 29-й строке (индекс 28)
        # Мы жестко задаем эти координаты, чтобы не зависеть от объединенных ячеек
        try:
            # Берем данные начиная с 30-й строки (индекс 29), чтобы пропустить заголовок и шапку
            df_hours = raw_df.iloc[29:].copy()
            
            # Задаем названия колонок вручную, как они должны быть
            # (основываясь на структуре вашего файла)
            df_hours.columns = ['Бренд', 'Филиал', 'ID филиала', 'Час', 'Метрика', 'Причина', 'Случаев', 'Дат', 'Заказы с ID', 'Случаи / заказы', 'Доля причины', 'Пусто1', 'Пусто2', 'Пусто3']
            
            # Очищаем от пустых строк и оставляем только нужные колонки
            df_hours = df_hours.dropna(subset=['Час', 'Причина', 'Случаев'])
            df_hours = df_hours[['Филиал', 'Час', 'Метрика', 'Причина', 'Случаев']]
            
            # Превращаем "Случаев" в числа
            df_hours['Случаев'] = pd.to_numeric(df_hours['Случаев'], errors='coerce').fillna(0)

            if not df_hours.empty:
                # Выбор филиала
                branches_in_hours = df_hours['Филиал'].dropna().unique()
                selected_branch = st.selectbox("Выберите точку для детального анализа:", branches_in_hours)
                
                filtered_hours = df_hours[df_hours['Филиал'] == selected_branch]
                
                if not filtered_hours.empty:
                    fig_reasons = px.bar(filtered_hours, x='Час', y='Случаев', color='Причина', 
                                         title=f"Причины по часам: {selected_branch}",
                                         labels={'Случаев': 'Количество инцидентов'})
                    st.plotly_chart(fig_reasons, use_container_width=True)
                    
                    st.info("**Как читать график:** Каждый цветной блок — это конкретная причина. Высота столбца показывает, сколько раз эта причина встречалась в это время. Например, если видите высокий столбец 'Отсутствует позиция' в 18:00, значит, вечером закончилась еда.")
                else:
                    st.warning("Нет данных по выбранной точке.")
            else:
                st.warning("Таблица по часам пуста или не распознана.")
                
        except Exception as e:
            st.error(f"Ошибка при обработке таблицы по часам: {e}")
            st.info("Возможно, структура файла немного отличается. Попробуйте обновить страницу.")

except Exception as e:
    st.error(f"Общая ошибка при чтении файла: {e}")
