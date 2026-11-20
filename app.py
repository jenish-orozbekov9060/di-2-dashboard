import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Пульт Качества", layout="wide")
st.title("Пульт Качества (Ди-2)")

# Читаем Excel. Так как в файле есть шапки, мы указываем нужные листы и пропускаем строки
# (Обратите внимание: pandas может ругаться на формат, поэтому мы читаем сырые данные)
file_path = "data.xlsx"

try:
    # 1. Читаем таблицу с филиалами (находится на листе "Сводная", пропускаем 6 строк заголовков)
    df_branches = pd.read_excel(file_path, sheet_name="Сводная", skiprows=9, nrows=2)
    df_branches = df_branches[['Филиал', 'Все отмены', 'Партн. отмены', 'Неверные', 'Бэдфуд']]
    
    # 2. Читаем таблицу с причинами по часам
    # (Находим строку, где начинается "Причины по часам")
    df_hours = pd.read_excel(file_path, sheet_name="Сводная", skiprows=26) 
    # Очищаем от пустых строк и оставляем нужные колонки
    df_hours = df_hours.dropna(subset=['Час', 'Причина'])
    df_hours = df_hours[['Филиал', 'Час', 'Метрика', 'Причина', 'Случаев']]

    # --- БЛОК KPI ---
    st.subheader("1. Инциденты по филиалам")
    # Переводим в числа (на случай, если Excel отдал текст)
    df_branches['Партн. отмены'] = pd.to_numeric(df_branches['Партн. отмены'], errors='coerce')
    df_branches['Неверные'] = pd.to_numeric(df_branches['Неверные'], errors='coerce')
    df_branches['Бэдфуд'] = pd.to_numeric(df_branches['Бэдфуд'], errors='coerce')

    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Сводка по точкам:**")
        st.dataframe(df_branches, hide_index=True)
        
    with col2:
        # Строим график по филиалам
        fig_branch = px.bar(df_branches, x='Филиал', y=['Партн. отмены', 'Неверные', 'Бэдфуд'], 
                            title="Партнерские инциденты", barmode='group')
        st.plotly_chart(fig_branch, use_container_width=True)

    st.divider()

    # --- БЛОК АНАЛИЗА ПРИЧИН ---
    st.subheader("2. В какое время и почему происходят инциденты?")
    
    # Выбор филиала для детального просмотра
    selected_branch = st.selectbox("Выберите точку для детального анализа:", df_hours['Филиал'].unique())
    
    # Фильтруем данные по выбранной точке
    filtered_hours = df_hours[df_hours['Филиал'] == selected_branch]
    
    if not filtered_hours.empty:
        # Строим график причин
        fig_reasons = px.bar(filtered_hours, x='Час', y='Случаев', color='Причина', 
                             title=f"Причины по часам: {selected_branch}",
                             labels={'Случаев': 'Количество инцидентов'})
        st.plotly_chart(fig_reasons, use_container_width=True)
        
        st.info("**Как читать график:** Каждый цветной блок — это конкретная причина. Высота столбца показывает, сколько раз эта причина встречалась в это время. Например, если видите высокий столбец 'Отсутствует позиция' в 18:00, значит, вечером закончилась еда.")
    else:
        st.warning("Для этой точки нет детальных данных по часам.")

except Exception as e:
    st.error(f"Ошибка при чтении файла: {e}")