import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Пульт Качества (Ди-2)", layout="wide")
st.title("Пульт Качества (Ди-2)")
st.caption("Период анализа: 19 октября — 15 ноября 2026 года")

file_path = "data.xlsx"

try:
    raw_df = pd.read_excel(file_path, sheet_name="Сводная", header=None)

    # ============================================================
    # БЛОК 1: ИНЦИДЕНТЫ ПО ФИЛИАЛАМ
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

        # ============================================================
        # ПАРСИНГ БЛОКА 2: ПРИЧИНЫ ПО ЧАСАМ
        # ============================================================
        try:
            df_hours = raw_df.iloc[29:].copy()
            new_columns = ['Бренд', 'Филиал', 'ID филиала', 'Час', 'Метрика', 'Причина', 'Случаев', 'Дат', 'Заказы с ID', 'Случаи / заказы', 'Доля причины', 'Пусто1', 'Пусто2', 'Пусто3']
            df_hours = df_hours.iloc[:, :14]
            df_hours.columns = new_columns
            
            df_hours = df_hours.dropna(subset=['Час', 'Причина', 'Случаев'])
            df_hours = df_hours[['Филиал', 'Час', 'Метрика', 'Причина', 'Случаев']]
            df_hours['Случаев'] = pd.to_numeric(df_hours['Случаев'], errors='coerce').fillna(0)

            # --- АВТОМАТИЧЕСКИЙ ВЫВОД (ИСПРАВЛЕННЫЙ) ---
            if not df_hours.empty and not df_branches.empty:
                # Находим самую проблемную точку
                worst_branch = df_branches.loc[df_branches['Партн. отмены'].idxmax(), 'Филиал']
                worst_branch_data = df_hours[df_hours['Филиал'] == worst_branch].copy()
                
                if not worst_branch_data.empty:
                    # 1. Отфильтровываем мусорные строки (где написано "Все" или нет двоеточия в часах)
                    clean_data = worst_branch_data[
                        (~worst_branch_data['Час'].astype(str).str.contains('Все', case=False, na=False)) &
                        (~worst_branch_data['Причина'].astype(str).str.contains('Все', case=False, na=False)) &
                        (worst_branch_data['Час'].astype(str).str.contains(':', na=False))
                    ].copy()

                    if not clean_data.empty:
                        # Самый частый час
                        top_hour_series = clean_data.groupby('Час')['Случаев'].sum()
                        top_hour = top_hour_series.idxmax()
                        top_hour_cases = int(top_hour_series.max())
                        
                        # Самая частая причина
                        top_reason_series = clean_data.groupby('Причина')['Случаев'].sum()
                        top_reason = top_reason_series.idxmax()
                        top_reason_cases = int(top_reason_series.max())
                        
                        st.error(f"🚨 **Главная точка боли:** {worst_branch} \n\n"
                                 f"📍 **Пиковый час:** {top_hour} (инцидентов: {top_hour_cases}) \n\n"
                                 f"⚠️ **Самая частая причина:** {top_reason} (случаев: {top_reason_cases}) \n\n"
                                 f"*Рекомендуется обратить внимание на работу кухни в это время.*")
                    else:
                        st.warning("Не удалось выделить конкретный час (в данных только общие цифры).")

            st.divider()

            # --- ОТРИСОВКА БЛОКА 1 ---
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

            # --- ОТРИСОВКА БЛОКА 2 ---
            st.subheader("2. В какое время и почему происходят инциденты?")
            if not df_hours.empty:
                branches_in_hours = df_hours['Филиал'].dropna().unique()
                selected_branch = st.selectbox("Выберите точку для детального анализа:", branches_in_hours)
                
                filtered_hours = df_hours[df_hours['Филиал'] == selected_branch]
                
                # Фильтруем для графика, чтобы не было "Все"
                filtered_hours = filtered_hours[
                    (~filtered_hours['Час'].astype(str).str.contains('Все', case=False, na=False)) &
                    (filtered_hours['Час'].astype(str).str.contains(':', na=False))
                ]

                if not filtered_hours.empty:
                    fig_reasons = px.bar(filtered_hours, x='Час', y='Случаев', color='Причина', 
                                         title=f"Причины по часам: {selected_branch}",
                                         labels={'Случаев': 'Количество инцидентов'})
                    st.plotly_chart(fig_reasons, use_container_width=True)
                    
                    st.info("**Как читать график:** Каждый цветной блок — это конкретная причина. Высота столбца показывает, сколько раз эта причина встречалась в это время.")
                else:
                    st.warning("Нет детальных данных по часам для этой точки.")
            else:
                st.warning("Таблица по часам пуста.")
                
        except Exception as e:
            st.error(f"Ошибка при обработке таблицы по часам: {e}")

except Exception as e:
    st.error(f"Общая ошибка при чтении файла: {e}")
