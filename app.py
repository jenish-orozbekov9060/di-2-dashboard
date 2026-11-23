import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

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

# Умная сортировка для строковых дат (например, "1.11" и "19.10")
def smart_date_sort(df, date_col, time_col):
    try:
        # Пытаемся преобразовать в datetime, понимая точки
        temp_dates = df[date_col].astype(str).str.replace('.', '-', regex=False)
        # Если есть год (3 части), или без года (2 части)
        parsed = pd.to_datetime(temp_dates, dayfirst=True, errors='coerce')
        if parsed.isna().all():
            return df.sort_values(by=[date_col, time_col])
        
        df = df.copy()
        df['temp_sort_date'] = parsed
        return df.sort_values(by=['temp_sort_date', time_col])
    except:
        return df.sort_values(by=[date_col, time_col])

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
        df_branches.columns = raw_df.iloc[header_row].values
        
        df_points = df_branches[~df_branches['Филиал'].astype(str).str.contains('Итого', case=False, na=False)].copy()
        df_points = df_points[df_points['Филиал'].astype(str).str.strip() != '']

        cols_to_num = ['Заказы с ID', 'Партн. отмены', 'Неверные', 'Бэдфуд']
        for col in cols_to_num:
            if col in df_points.columns:
                df_points[col] = pd.to_numeric(df_points[col], errors='coerce').fillna(0)
            else:
                df_points[col] = 0 

        df_points['% Отмен'] = safe_divide(df_points['Партн. отмены'], df_points['Заказы с ID'])
        df_points['% Неверных'] = safe_divide(df_points['Неверные'], df_points['Заказы с ID'])
        df_points['% БФ'] = safe_divide(df_points['Бэдфуд'], df_points['Заказы с ID'])

        st.divider()
        st.subheader("📍 Детализация по точкам")
        
        if not df_points.empty:
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
            # 2. ГРАФИК (Теперь защищен от пустых данных)
            # ============================================================
            st.subheader("📊 Визуальное сравнение")
            fig = go.Figure()
            fig.add_bar(name="Отмены, %", x=df_points['Филиал'], y=df_points['% Отмен'], marker_color='#D64545', text=df_points['% Отмен'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
            fig.add_bar(name="Вронги, %", x=df_points['Филиал'], y=df_points['% Неверных'], marker_color='#E6A700', text=df_points['% Неверных'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
            fig.add_bar(name="БФ, %", x=df_points['Филиал'], y=df_points['% БФ'], marker_color='#2E9E4F', text=df_points['% БФ'].apply(lambda x: f"{x:.2f}%"), textposition="outside")
            
            fig.add_hline(y=TARGETS['cancels'], line_dash="dash", line_color="#D64545", annotation_text=f"Цель отмен {TARGETS['cancels']}%", annotation_position="top left")
            fig.add_hline(y=TARGETS['wrongs'], line_dash="dash", line_color="#E6A700", annotation_text=f"Цель вронгов {TARGETS['wrongs']}%", annotation_position="top left")
            fig.add_hline(y=TARGETS['bf'], line_dash="dash", line_color="#2E9E4F", annotation_text=f"Цель БФ {TARGETS['bf']}%", annotation_position="bottom left")
            
            fig.update_layout(barmode='group', yaxis_title="%", margin=dict(t=40, b=40, l=40, r=40))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных по отдельным филиалам для отображения графиков.")

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
            df_hours.columns = raw_df.iloc[hour_header_idx].values
            
            df_hours = df_hours.dropna(subset=['Час', 'Причина'])
            
            if 'Случаев' in df_hours.columns:
                df_hours['Случаев'] = pd.to_numeric(df_hours['Случаев'], errors='coerce').fillna(0)
            else:
                df_hours['Случаев'] = 0

            if 'Дат' in df_hours.columns:
                df_hours['Дат'] = df_hours['Дат'].astype(str).str.split(' ').str[0].str.replace('.0', '', regex=False)
            else:
                df_hours['Дат'] = "Без даты"

            # Убрали жесткую проверку на ':' (чтобы не отсеять часы без двоеточия)
            df_hours_clean = df_hours[
                (~df_hours['Час'].astype(str).str.contains('Все', case=False, na=False)) &
                (~df_hours['Причина'].astype(str).str.contains('Все', case=False, na=False))
            ]

            st.subheader("⏰ Когда и почему?")
            if not df_hours_clean.empty:
                branches_in_hours = df_hours_clean['Филиал'].dropna().unique() if 'Филиал' in df_hours_clean.columns else []
                
                if len(branches_in_hours) > 0:
                    selected_branch = st.selectbox("Выберите точку для анализа:", branches_in_hours)
                    filtered_hours = df_hours_clean[df_hours_clean['Филиал'] == selected_branch].copy()
                    
                    if not filtered_hours.empty:
                        filtered_hours['День_Час'] = filtered_hours['Дат'] + " | " + filtered_hours['Час'].astype(str)

                        # Применяем умную сортировку
                        filtered_hours = smart_date_sort(filtered_hours, 'Дат', 'Час')

                        fig_reasons = px.bar(
                            filtered_hours, x='День_Час', y='Случаев', color='Причина', 
                            title=f"Причины по дням и часам: {selected_branch}",
                            labels={'День_Час': 'Дата | Время', 'Случаев': 'Кол-во'}
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
                    st.warning("В данных по причинам не найдена колонка 'Филиал'.")
            else:
                st.info("Нет детальных данных по причинам.")
        else:
            st.warning("В файле не найден блок с причинами.")
            
    else:
        st.error("Не удалось найти шапку таблицы с филиалами (ожидались колонки 'Филиал' и 'Заказы с ID').")

except Exception as e:
    # Теперь ошибка будет более информативной
    st.error(f"Произошла ошибка: {type(e).__name__}.")
    st.exception(e) # Выводит полный стек ошибки (помогает при отладке)
