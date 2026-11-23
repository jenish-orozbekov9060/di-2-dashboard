import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# НАСТРОЙКИ ПАРТНЕРА
# ============================================================
PARTNER_NAME = "Ди-2" 
# ============================================================

st.set_page_config(page_title=f"Пульт Качества ({PARTNER_NAME})", layout="wide")
st.title(f"Пульт Качества: {PARTNER_NAME}")
st.caption("Период анализа: 19 октября — 15 ноября 2026 года")

TARGETS = {"cancels": 0.80, "wrongs": 0.60, "bf": 0.30}

def render_metric_card(col, label, value, target):
    color = "#2E9E4F" if value <= target else "#D64545"
    diff = value - target
    diff_text = f"+{diff:.2f}%" if diff > 0 else f"{diff:.2f}%"
    
    col.markdown(
        f"""
        <div style="padding:10px; border-radius:8px; background-color:#f8f9fa; text-align:center; border: 1px solid #ddd; height: 100%;">
            <div style="font-size:14px; color:#666; margin-bottom:4px; font-weight:bold;">{label}</div>
            <div style="font-size:28px; font-weight:bold; color:{color};">{value:.2f}%</div>
            <div style="font-size:12px; color:#888;">Цель: ≤ {target}%</div>
            <div style="font-size:12px; color:{color}; font-weight:bold;">({diff_text})</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def safe_divide(a, b):
    if not isinstance(a, pd.Series): a = pd.Series([a]*len(b), index=b.index)
    return (a / b.replace(0, float('nan'))).fillna(0) * 100

def clean_columns(cols):
    """Убирает дубликаты и пустые названия колонок (лечит DuplicateError)"""
    clean_cols = []
    seen = {}
    for i, col in enumerate(cols):
        c_str = str(col).strip()
        if c_str == 'nan' or c_str == '' or pd.isna(col):
            c_str = f"Unnamed_{i}"
        
        if c_str in seen:
            seen[c_str] += 1
            clean_cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            clean_cols.append(c_str)
    return clean_cols

file_path = "data.xlsx"

try:
    raw_df = pd.read_excel(file_path, sheet_name=0, header=None)

    # ============================================================
    # 1. ПОИСК ТАБЛИЦЫ ФИЛИАЛОВ
    # ============================================================
    header_row = None
    for i, row in raw_df.iterrows():
        row_values = [str(val).strip() for val in row.values]
        if 'Филиал' in row_values and ('Заказы с ID' in row_values or 'Все отмены' in row_values):
            header_row = i
            break
            
    if header_row is not None:
        df_branches = raw_df.iloc[header_row + 1 :].copy()
        df_branches.columns = clean_columns(raw_df.iloc[header_row].values)
        
        # ЖЕСТКАЯ ФИЛЬТРАЦИЯ: убираем "Итого", пустые строки и строки "nan"
        df_points = df_branches.copy()
        df_points['Филиал'] = df_points['Филиал'].astype(str).str.strip()
        df_points = df_points[
            (df_points['Филиал'].str.lower() != 'nan') & 
            (df_points['Филиал'].str.lower() != '') & 
            (~df_points['Филиал'].str.contains('Итого', case=False, na=False))
        ]

        # Конвертация в числа
        cols_to_num = ['Заказы с ID', 'Партн. отмены', 'Неверные', 'Бэдфуд']
        for col in cols_to_num:
            if col in df_points.columns:
                df_points[col] = pd.to_numeric(df_points[col], errors='coerce').fillna(0)
            else:
                df_points[col] = 0 

        # Считаем проценты
        df_points['% Отмен'] = safe_divide(df_points['Партн. отмены'], df_points['Заказы с ID'])
        df_points['% Неверных'] = safe_divide(df_points['Неверные'], df_points['Заказы с ID'])
        df_points['% БФ'] = safe_divide(df_points['Бэдфуд'], df_points['Заказы с ID'])

        st.divider()
        st.subheader("📍 Детализация по точкам")
        
        if not df_points.empty:
            # Рендер карточек
            for i in range(0, len(df_points), 3):
                cols = st.columns(3)
                chunk = df_points.iloc[i:i+3]
                for idx, (index, row) in enumerate(chunk.iterrows()):
                    with cols[idx]:
                        st.markdown(f"#### {row['Филиал']}")
                        render_metric_card(st, "Отмены", row['% Отмен'], TARGETS['cancels'])
                        st.write("") 
                        render_metric_card(st, "Вронги", row['% Неверных'], TARGETS['wrongs'])
                        st.write("")
                        render_metric_card(st, "БФ (Брак)", row['% БФ'], TARGETS['bf'])
                        st.write("---")

            st.divider()
            
            # ============================================================
            # 2. ГРАФИК (В стиле "Шаурмы")
            # ============================================================
            st.subheader("📊 Визуальное сравнение")
            
            # Используем темную тему Plotly и задаем цвета
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Отмены, %", x=df_points['Филиал'], y=df_points['% Отмен'], 
                marker_color='#ef4444', text=df_points['% Отмен'].apply(lambda x: f"{x:.2f}%"), textposition="outside"
            ))
            fig.add_trace(go.Bar(
                name="Вронги, %", x=df_points['Филиал'], y=df_points['% Неверных'], 
                marker_color='#f59e0b', text=df_points['% Неверных'].apply(lambda x: f"{x:.2f}%"), textposition="outside"
            ))
            fig.add_trace(go.Bar(
                name="БФ, %", x=df_points['Филиал'], y=df_points['% БФ'], 
                marker_color='#10b981', text=df_points['% БФ'].apply(lambda x: f"{x:.2f}%"), textposition="outside"
            ))
            
            # Добавляем линии целей
            fig.add_hline(y=TARGETS['cancels'], line_dash="dash", line_color="#ef4444", annotation_text=f"Цель отмен {TARGETS['cancels']}%", annotation_position="top left")
            fig.add_hline(y=TARGETS['wrongs'], line_dash="dash", line_color="#f59e0b", annotation_text=f"Цель вронгов {TARGETS['wrongs']}%", annotation_position="top left")
            fig.add_hline(y=TARGETS['bf'], line_dash="dash", line_color="#10b981", annotation_text=f"Цель БФ {TARGETS['bf']}%", annotation_position="bottom left")
            
            fig.update_layout(
                barmode='group', 
                yaxis_title="%", 
                template="plotly_dark", # Темная тема как на скрине
                margin=dict(t=50, b=40, l=40, r=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("Нет валидных данных по филиалам.")

        st.divider()

        # ============================================================
        # 3. ПРИЧИНЫ ПО ДНЯМ И ЧАСАМ
        # ============================================================
        hour_header_idx = None
        for i, row in raw_df.iterrows():
            if 'Час' in row.values and 'Причина' in row.values:
                hour_header_idx = i
                break

        if hour_header_idx is not None:
            df_hours = raw_df.iloc[hour_header_idx + 1:].copy()
            # Применяем функцию очистки колонок (лечит DuplicateError)
            df_hours.columns = clean_columns(raw_df.iloc[hour_header_idx].values)
            
            df_hours = df_hours.dropna(subset=['Час', 'Причина'])
            
            if 'Случаев' in df_hours.columns:
                df_hours['Случаев'] = pd.to_numeric(df_hours['Случаев'], errors='coerce').fillna(0)
            else:
                df_hours['Случаев'] = 0

            if 'Дат' in df_hours.columns:
                df_hours['Дат'] = df_hours['Дат'].astype(str).str.split(' ').str[0].str.replace('.0', '', regex=False)
            else:
                df_hours['Дат'] = "Без даты"

            df_hours_clean = df_hours[
                (~df_hours['Час'].astype(str).str.contains('Все', case=False, na=False)) &
                (~df_hours['Причина'].astype(str).str.contains('Все', case=False, na=False))
            ]

            st.subheader("⏰ Когда и почему?")
            if not df_hours_clean.empty and 'Филиал' in df_hours_clean.columns:
                branches_in_hours = df_hours_clean['Филиал'].dropna().unique()
                # Фильтруем nan из списка филиалов
                branches_in_hours = [b for b in branches_in_hours if str(b).lower() != 'nan']
                
                if len(branches_in_hours) > 0:
                    selected_branch = st.selectbox("Выберите точку для анализа:", branches_in_hours)
                    filtered_hours = df_hours_clean[df_hours_clean['Филиал'] == selected_branch].copy()
                    
                    if not filtered_hours.empty:
                        filtered_hours['День_Час'] = filtered_hours['Дат'] + " | " + filtered_hours['Час'].astype(str)

                        fig_reasons = px.bar(
                            filtered_hours, x='День_Час', y='Случаев', color='Причина', 
                            title=f"Причины по дням и часам: {selected_branch}",
                            labels={'День_Час': 'Дата | Время', 'Случаев': 'Кол-во'},
                            template="plotly_dark" # Тоже делаем темным для единообразия
                        )
                        fig_reasons.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig_reasons, use_container_width=True)
                        
                        st.markdown("---")
                        st.subheader("📋 Детальный список")
                        display_cols = [c for c in ['Дат', 'Час', 'Метрика', 'Причина', 'Случаев'] if c in filtered_hours.columns]
                        display_df_h = filtered_hours[display_cols].copy()
                        rename_map = {'Дат': 'Дата', 'Час': 'Время', 'Метрика': 'Тип', 'Причина': 'Причина', 'Случаев': 'Кол-во'}
                        display_df_h = display_df_h.rename(columns=rename_map)
                        st.dataframe(display_df_h, hide_index=True, use_container_width=True)
                else:
                    st.warning("В данных по причинам не найдено валидных филиалов.")
            else:
                st.info("Нет детальных данных по причинам.")
        else:
            st.warning("В файле не найден блок с причинами.")
            
    else:
        st.error("Не удалось найти шапку таблицы с филиалами (ожидались колонки 'Филиал' и 'Заказы с ID').")

except Exception as e:
    st.error(f"Произошла ошибка: {type(e).__name__}.")
    st.exception(e)
