import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Пульт Качества (Ди-2)", layout="wide")
st.title("Пульт Качества (Ди-2)")
st.caption("Период анализа: 19 октября — 15 ноября 2026 года")

# --- ТАРГЕТЫ (ЦЕЛИ) ---
TARGETS = {
    "cancels": 0.80,
    "wrongs": 0.60,
    "bf": 0.30
}

file_path = "data.xlsx"

try:
    raw_df = pd.read_excel(file_path, sheet_name="Сводная", header=None)

    # ============================================================
    # 1. ПОИСК ТАБЛИЦЫ ФИЛИАЛОВ
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
        
        cols_to_keep = ['Филиал', 'Заказы с ID', 'Все отмены', 'Партн. отмены', 'Неверные', 'Бэдфуд']
        available_cols = [c for c in cols_to_keep if c in df_branches.columns]
        df_branches = df_branches[available_cols].dropna(subset=['Филиал'])

        # Переводим в числа
        for col in cols_to_keep[1:]:
            if col in df_branches.columns:
                df_branches[col] = pd.to_numeric(df_branches[col], errors='coerce').fillna(0)

        # --- РАСЧЕТ ПРОЦЕНТОВ И ПРОВЕРКА ТАРГЕТОВ ---
        # Защита от деления на ноль
        df_branches['Заказы с ID'] = df_branches['Заказы с ID'].replace(0, 1) 
        
        df_branches['% Отмен'] = (df_branches['Партн. отмены'] / df_branches['Заказы с ID']) * 100
        df_branches['% Неверных'] = (df_branches['Неверные'] / df_branches['Заказы с ID']) * 100
        df_branches['% БФ'] = (df_branches['Бэдфуд'] / df_branches['Заказы с ID']) * 100

        # ============================================================
        # 2. ВЕРХНИЙ БЛОК: KPI-КАРТОЧКИ БРЕНДА (С ТАРГЕТАМИ)
        # ============================================================
        st.subheader("1. Общая картина по бренду (Итого)")
        
        total_row = df_branches[df_branches['Филиал'] == 'Итого']
        if not total_row.empty:
            total_cancels = total_row['% Отмен'].values[0]
            total_wrongs = total_row['% Неверных'].values[0]
            total_bf = total_row['% БФ'].values[0]
            
            c1, c2, c3 = st.columns(3)
            
            # Карточка Отмен
            color_c = "green" if total_cancels <= TARGETS['cancels'] else "red"
            c1.markdown(f"<h3>Отмены</h3><h1 style='color:{color_c}; margin:0;'>{total_cancels:.2f}%</h1><p style='margin:0;'>Цель: ≤ {TARGETS['cancels']}%</p>", unsafe_allow_html=True)
            
            # Карточка Вронгов
            color_w = "green" if total_wrongs <= TARGETS['wrongs'] else "red"
            c2.markdown(f"<h3>Вронги (сборка)</h3><h1 style='color:{color_w}; margin:0;'>{total_wrongs:.2f}%</h1><p style='margin:0;'>Цель: ≤ {TARGETS['wrongs']}%</p>", unsafe_allow_html=True)
            
            # Карточка БФ
            color_b = "green" if total_bf <= TARGETS['bf'] else "red"
            c3.markdown(f"<h3>БФ (качество)</h3><h1 style='color:{color_b}; margin:0;'>{total_bf:.2f}%</h1><p style='margin:0;'>Цель: ≤ {TARGETS['bf']}%</p>", unsafe_allow_html=True)

        st.divider()

        # ============================================================
        # 3. ДЕТАЛИЗАЦИЯ ПО ТОЧКАМ
        # ============================================================
        st.subheader("2. Детализация по филиалам")
        
        # Убираем строку "Итого" для графика, чтобы не мешала
        df_points = df_branches[df_branches['Филиал'] != 'Итого'].copy()
        
        col1, col2 = st.columns(2)
        with col1:
            # Строим график процентов
            fig = go.Figure()
            fig.add_bar(name="Отмены, %", x=df_points['Филиал'], y=df_points['% Отмен'], marker_color='#D64545', text=df_points['% Отмен'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
            fig.add_bar(name="Неверные, %", x=df_points['Филиал'], y=df_points['% Неверных'], marker_color='#E6A700', text=df_points['% Неверных'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
            fig.add_bar(name="БФ, %", x=df_points['Филиал'], y=df_points['% БФ'], marker_color='#2E9E4F', text=df_points['% БФ'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
            
            # Добавляем линии таргетов
            fig.add_hline(y=TARGETS['cancels'], line_dash="dash", line_color="#D64545", annotation_text=f"Цель отмен {TARGETS['cancels']}%", annotation_position="top left")
            fig.add_hline(y=TARGETS['wrongs'], line_dash="dash", line_color="#E6A700", annotation_text=f"Цель вронгов {TARGETS['wrongs']}%", annotation_position="top left")
            fig.add_hline(y=TARGETS['bf'], line_dash="dash", line_color="#2E9E4F", annotation_text=f"Цель БФ {TARGETS['bf']}%", annotation_position="bottom left")
            
            fig.update_layout(barmode='group', title="Сравнение филиалов с таргетами", yaxis_title="%", margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Таблица с процентами
            st.write("**Таблица показателей (в %):**")
            display_df = df_points[['Филиал', '% Отмен', '% Неверных', '% БФ']].copy()
            display_df.columns = ['Филиал', 'Отмены %', 'Неверные %', 'БФ %']
            
            # Форматируем проценты
            display_df['Отмены %'] = display_df['Отмены %'].apply(lambda x: f"{x:.2f}%")
            display_df['Неверные %'] = display_df['Неверные %'].apply(lambda x: f"{x:.2f}%")
            display_df['БФ %'] = display_df['БФ %'].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(display_df, hide_index=True, use_container_width=True)
            
            st.info(f"**Как читать:**\nЗеленый цвет — мы в норме. Красный — превысили таргет.\n\n"
                    f"• Отмены: норма ≤ {TARGETS['cancels']}%\n"
                    f"• Вронги: норма ≤ {TARGETS['wrongs']}%\n"
                    f"• БФ: норма ≤ {TARGETS['bf']}%")

        st.divider()

        # ============================================================
        # 4. БЛОК 2: ПРИЧИНЫ ПО ЧАСАМ
        # ============================================================
        # ... (Здесь идет ваш старый код для блока поиска часов, начиная с hour_header_idx = None)
        # Я его не менял, чтобы не перегружать ответ. Он остается точно таким же, как в предыдущем сообщении.
        
        # ВСТАВЬТЕ СЮДА БЛОК "hour_header_idx = None" И ВСЁ, ЧТО ИДЕТ НИЖЕ ДО КОНЦА.
        
        # (Для удобства я дублирую конец кода, чтобы вы могли просто скопировать все целиком)
        hour_header_idx = None
        for i, row in raw_df.iterrows():
            if 'Час' in row.values and 'Причина' in row.values:
                hour_header_idx = i
                break

        if hour_header_idx is not None:
            df_hours = raw_df.iloc[hour_header_idx + 1:].copy()
            df_hours.columns = raw_df.iloc[hour_header_idx].values
            
            cols_to_keep_h = ['Филиал', 'Час', 'Метрика', 'Причина', 'Случаев', 'Дат']
            available_cols_h = [c for c in cols_to_keep_h if c in df_hours.columns]
            df_hours = df_hours[available_cols_h].dropna(subset=['Час', 'Причина', 'Случаев'])
            
            df_hours['Случаев'] = pd.to_numeric(df_hours['Случаев'], errors='coerce').fillna(0)
            df_hours['Дат'] = pd.to_numeric(df_hours['Дат'], errors='coerce').fillna(0)

            df_hours_clean = df_hours[
                (~df_hours['Час'].astype(str).str.contains('Все', case=False, na=False)) &
                (~df_hours['Причина'].astype(str).str.contains('Все', case=False, na=False)) &
                (df_hours['Час'].astype(str).str.contains(':', na=False))
            ]

            st.subheader("3. В какое время и почему происходят инциденты?")
            if not df_hours_clean.empty:
                branches_in_hours = df_hours_clean['Филиал'].dropna().unique()
                selected_branch = st.selectbox("Выберите точку для детального анализа:", branches_in_hours)
                
                filtered_hours = df_hours_clean[df_hours_clean['Филиал'] == selected_branch]
                
                if not filtered_hours.empty:
                    fig_reasons = px.bar(filtered_hours, x='Час', y='Случаев', color='Причина', 
                                         title=f"Причины по часам: {selected_branch}",
                                         labels={'Случаев': 'Количество'})
                    st.plotly_chart(fig_reasons, use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader("📋 Детальный список")
                    display_df_h = filtered_hours[['Час', 'Метрика', 'Причина', 'Случаев', 'Дат']].copy()
                    display_df_h.columns = ['Время', 'Тип', 'Причина', 'Кол-во', 'Дней']
                    st.dataframe(display_df_h, hide_index=True, use_container_width=True)
                else:
                    st.warning("Нет детальных данных.")
            else:
                st.warning("Нет данных по часам.")
        else:
            st.error("Таблица по часам не найдена в файле.")

except Exception as e:
    st.error(f"Ошибка при чтении файла: {e}")
