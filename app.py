import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="Módulo Vacaciones", layout="wide")
# todo: add s3 integration to the data_loader (maybe boto3 or streamlit s3). 
@st.cache_data
def data_loader(uploaded_file=None):
    if uploaded_file is not None:
        data = pd.read_excel(uploaded_file)
    else:
        data = pd.read_excel("data/MockData_Vacaciones_Empleados.xlsx")

    data["Fecha inicio"] = pd.to_datetime(data["Fecha inicio vacaciones"])
    data["Fecha fin"] = pd.to_datetime(data["Fecha fin vacaciones"])
    data["Departamento"] = data["Departamento"].astype('category')
    data["Aprobado"] = data["Aprobado"].astype('category')
    data["Días"] = pd.to_numeric(data["Días"], errors='coerce')

    return data
@st.cache_data
def conflicts_detector(vacation_data):
    """
    todo: add none approved logic aswell to show ⚠️ and danger for non approved
    """
    conflicts_details = []
    approved_vacations = vacation_data[vacation_data["Aprobado"] == "Sí"].copy()
    
    if approved_vacations.empty:
        return conflicts_details
    
    for dept, dept_data in approved_vacations.groupby("Departamento"):
        dept_data = dept_data.sort_values("Fecha inicio").reset_index(drop=True)
        
        for i, current_employee in dept_data.iterrows():
            potential_conflicts = dept_data[
                (dept_data.index != i) &
                (dept_data["Fecha inicio"] <= current_employee["Fecha fin"]) &
                (dept_data["Fecha fin"] >= current_employee["Fecha inicio"])
            ]
            
            if not potential_conflicts.empty:
                conflicts_list = [
                    {
                        'conflicting_employee': row["Nombre"],
                        'conflict_start_date': row["Fecha inicio"],
                        'conflict_end_date': row["Fecha fin"]
                    }
                    for _, row in potential_conflicts.iterrows()
                ]
                
                conflicts_details.append({
                    'Nombre': current_employee["Nombre"],
                    'Departamento': current_employee["Departamento"],
                    'conflictos': conflicts_list,
                    'tooltip': f"Conflicto con: {', '.join(potential_conflicts['Nombre'].tolist())}"
                })
    
    return conflicts_details

@st.cache_data
def table_formatter(vacation_data, conflicts_details):
    if vacation_data.empty:
        return pd.DataFrame() 
    
    display_data = vacation_data.drop_duplicates(subset=['Nombre', 'Fecha inicio', 'Fecha fin']).copy()
    
    column_mapping = {
        'Nombre': 'Empleado',
        'Departamento': 'Departamento', 
        'Fecha inicio': 'Inicio de Vacaciones',
        'Fecha fin': 'Fin de Vacaciones',
        'Días': 'Días',
        'Aprobado': 'Estado'
    }
    
    display_data = display_data[list(column_mapping.keys())].rename(columns=column_mapping)
    
    display_data['Inicio de Vacaciones'] = display_data['Inicio de Vacaciones'].dt.strftime('%Y-%m-%d')
    display_data['Fin de Vacaciones'] = display_data['Fin de Vacaciones'].dt.strftime('%Y-%m-%d')
    
    conflicts_dict = {c['Nombre']: '⚠️' for c in conflicts_details}
    display_data.insert(0, '⚠️', display_data['Empleado'].map(conflicts_dict).fillna(''))
    
    return display_data

@st.cache_data
def employees_vacations_per_week(vacation_data):
    if vacation_data.empty:
        return pd.DataFrame()
    
    start_date = vacation_data["Fecha inicio"].min()
    end_date = vacation_data["Fecha fin"].max()
    
    
    week_starts = pd.date_range(
        start=start_date - timedelta(days=start_date.weekday()),
        end=end_date,
        freq='W-MON'
    )
    
    weekly_results = []
    for week_start in week_starts:
        week_end = week_start + timedelta(days=6)
        
        
        employees_on_vacation = vacation_data[
            (vacation_data["Fecha inicio"] <= week_end) & 
            (vacation_data["Fecha fin"] >= week_start)
        ]
        
        weekly_results.append({
            'week_label': f"Semana {week_start.strftime('%Y-%m-%d')}",
            'week_start': week_start,
            'empleados_vacaciones': len(employees_on_vacation),
            'empleados_detalles': employees_on_vacation[['Nombre', 'Departamento']].to_dict('records')
        })
    
    return pd.DataFrame(weekly_results)

@st.cache_data
def department_percentages(total_data, current_vacation_data):
    
    total_by_dept = total_data.groupby('Departamento', observed=True)['Nombre'].nunique()
    
    if current_vacation_data.empty:
        vacation_by_dept = pd.Series(dtype='int64', name='empleados_vacaciones')
        vacation_by_dept.index.name = 'Departamento'
    else:
        vacation_by_dept = current_vacation_data.groupby('Departamento', observed=True)['Nombre'].nunique()
    
    
    merged_data = pd.DataFrame({
        'total_empleados': total_by_dept,
        'empleados_vacaciones': vacation_by_dept
    })
    
    merged_data['empleados_vacaciones'] = merged_data['empleados_vacaciones'].fillna(0).astype('int64')
    
    merged_data['porcentaje_vacaciones'] = (
        merged_data['empleados_vacaciones'] / merged_data['total_empleados'] * 100
    )
    
    result = merged_data.reset_index()
    if result['Departamento'].dtype.name == 'category':
        result['Departamento'] = result['Departamento'].astype(str)
    
    return result

def get_filtered_data(data, departments, approval_status, date_range):
    """Efficient filtering with early returns"""
    if data.empty:
        return data
    
    filtered_data = data[
        data["Departamento"].isin(departments) &
        data["Aprobado"].isin(approval_status)
    ]
    
    if len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered_data = filtered_data[
            (filtered_data["Fecha inicio"] >= start_date) &
            (filtered_data["Fecha fin"] <= end_date)
        ]
    
    return filtered_data

@st.cache_data
def get_current_vacations(filtered_data, _today=None):
    
    if _today is None:
        _today = pd.Timestamp.now()
    
    return filtered_data[
        (filtered_data["Fecha inicio"] <= _today) & 
        (filtered_data["Fecha fin"] >= _today) &
        (filtered_data["Aprobado"] == "Sí")
    ]

def calculate_summary_metrics(filtered_data):
    
    if filtered_data.empty:
        return 0, 0.0, 0.0
    
    total_employees = len(filtered_data)
    avg_days = filtered_data["Días"].mean()
    approved_count = (filtered_data["Aprobado"] == "Sí").sum()
    approved_percentage = (approved_count / total_employees) * 100
    
    return total_employees, avg_days, approved_percentage

def render_summary_cards(total_emp, avg_days, approved_pct, current_vacations_count):
    
    """Render summary cards with cached CSS"""
    # if 'card_css_loaded' not in st.session_state:
    st.markdown("""
        <style>
            .card-container {
                background-color: #2d2f35;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: transform 0.2s;
            }
            .card-container:hover {
                transform: scale(1.02);
            }
            .card-title {
                font-size: 18px;
                color: #ffffff;
                margin-bottom: 5px;
            }
            .card-value {
                font-size: 32px;
                font-weight: bold;
                color: #ffffff;
            }
        </style>
    """, unsafe_allow_html=True)
        # st.session_state.card_css_loaded = True

    col1, col2, col3, col4 = st.columns(4, gap="large")

    cards_data = [
        ("Empleados filtrados", total_emp),
        ("Días promedio", f"{avg_days:.1f}"),
        ("Porcentaje aprobados", f"{approved_pct:.1f}%"),
        ("En vacaciones", current_vacations_count)
    ]

    for col, (title, value) in zip([col1, col2, col3, col4], cards_data):
        with col:
            st.markdown(f"""
                <div class="card-container">
                    <div class="card-title">{title}</div>
                    <div class="card-value">{value}</div>
                </div>
            """, unsafe_allow_html=True)


def render_table_view(filtered_data):
    st.subheader("📋 Vacaciones de Empleados")
    
    if filtered_data.empty:
        st.info("No hay datos para mostrar en la tabla")
        return
    
    conflicts_detail = conflicts_detector(filtered_data)
    formatted_table = table_formatter(filtered_data, conflicts_detail)
    
    column_config = {
        "⚠️": st.column_config.TextColumn(
            "⚠️", help="Indica conflictos de fechas", width="small"
        ),
        "Empleado": st.column_config.TextColumn("Empleado", width="medium"),
        "Departamento": st.column_config.TextColumn("Departamento", width="medium"),
        "Inicio de Vacaciones": st.column_config.DateColumn(
            "Inicio de Vacaciones", format="YYYY-MM-DD", width="medium"
        ),
        "Fin de Vacaciones": st.column_config.DateColumn(
            "Fin de Vacaciones", format="YYYY-MM-DD", width="medium"
        ),
        "Días": st.column_config.NumberColumn("Días", width="small"),
        "Estado": st.column_config.TextColumn("Estado", width="small")
    }
    
    st.dataframe(formatted_table, use_container_width=True, hide_index=True, column_config=column_config)
    
    # TODO: create advanced tool to manage conflicts and show them in easy to consume format
    has_conflicts = any(len(c['conflictos']) > 0 for c in conflicts_detail)
    if has_conflicts:
        conflicting_depts = list(set(c['Departamento'] for c in conflicts_detail))
        st.warning(f"⚠️ Conflictos detectados en: {', '.join(conflicting_depts)}")

def render_gantt_view(filtered_data):
    st.subheader("Diagrama de Gantt de Vacaciones")
    
    if filtered_data.empty:
        st.info("No hay datos para mostrar en el diagrama de Gantt")
        return
    
    gantt_data = filtered_data[['Nombre', 'Fecha inicio', 'Fecha fin', 'Departamento']].copy()
    gantt_data = gantt_data.rename(columns={'Nombre': 'Empleado'})
    
    fig = px.timeline(
        gantt_data,
        x_start="Fecha inicio",
        x_end="Fecha fin",
        y="Empleado",
        color="Departamento"
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)


def render_weekly_stats(filtered_data):
    st.subheader("📊 Empleados en Vacaciones por Semana")
    
    if filtered_data.empty:
        st.info("No hay datos suficientes para mostrar estadísticas por semana")
        return
    
    weekly_data = employees_vacations_per_week(filtered_data)
    
    if weekly_data.empty:
        st.info("No hay datos de semanas para mostrar")
        return
    
    fig_weekly = px.line(
        weekly_data, 
        x='week_start', 
        y='empleados_vacaciones',
        title='Número de Empleados en Vacaciones por Semana',
        labels={'empleados_vacaciones': 'Empleados en Vacaciones', 'week_start': 'week_label'}
    )
    fig_weekly.update_traces(mode='lines+markers')
    st.plotly_chart(fig_weekly, use_container_width=True)
    
    metrics_data = weekly_data['empleados_vacaciones']
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Máximo empleados/semana", metrics_data.max())
    with col2:
        st.metric("Promedio empleados/semana", f"{metrics_data.mean():.1f}")
    with col3:
        st.metric("Semanas con vacaciones", (metrics_data > 0).sum())

    st.subheader("Detalle por Semana")
    display_weekly = weekly_data[['week_label', 'empleados_vacaciones']].copy()
    display_weekly.columns = ['Semana', 'Empleados en Vacaciones']
    st.dataframe(display_weekly, use_container_width=True)


def render_department_dashboard(data, current_vacations):
    st.subheader("🏢 Dashboard de Vacaciones por Departamento")
    
    if current_vacations.empty:
        st.info("No hay empleados actualmente en vacaciones para mostrar estadísticas por departamento")
        
        st.subheader("Distribución General por Departamento")
        dept_distribution = data.groupby("Departamento").size().reset_index(name="Cantidad")
        fig_general = px.bar(
            dept_distribution, 
            x="Departamento", 
            y="Cantidad", 
            title="Total de Registros de Vacaciones por Departamento"
        )
        st.plotly_chart(fig_general, use_container_width=True)
        return
    
    department_stats = department_percentages(data, current_vacations)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_percentage = px.bar(
            department_stats,
            x='Departamento',
            y='porcentaje_vacaciones',
            title='Porcentaje de Empleados en Vacaciones por Departamento',
            labels={'porcentaje_vacaciones': 'Porcentaje en Vacaciones (%)'},
            color='porcentaje_vacaciones',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_percentage, use_container_width=True)
    
    with col2:
        vacation_distribution = current_vacations.groupby('Departamento').size().reset_index(name='count')
        fig_donut = px.pie(
            vacation_distribution,
            values='count',
            names='Departamento',
            title='Distribución de Empleados Actualmente en Vacaciones'
        )
        fig_donut.update_traces(hole=0.4)
        st.plotly_chart(fig_donut, use_container_width=True)
    
    st.subheader("Resumen Consolidado por Departamento")
    
    duration_stats = data.groupby('Departamento', observed=True)['Días'].agg(['mean', 'count']).reset_index()
    duration_stats.columns = ['Departamento', 'Días Promedio', 'Cantidad Solicitudes']
    duration_stats['Días Promedio'] = duration_stats['Días Promedio'].round(1)
    
    if duration_stats['Departamento'].dtype.name == 'category':
        duration_stats['Departamento'] = duration_stats['Departamento'].astype(str)
    
    consolidated_table = department_stats.merge(duration_stats, on='Departamento', how='left')
    
    consolidated_table['Cantidad Solicitudes'] = consolidated_table['Cantidad Solicitudes'].fillna(0).astype(int)
    consolidated_table['Días Promedio'] = consolidated_table['Días Promedio'].fillna(0.0).round(1)
    consolidated_table['porcentaje_vacaciones'] = consolidated_table['porcentaje_vacaciones'].round(1)
    
    final_columns = {
        'Departamento': 'Departamento',
        'total_empleados': 'Total Empleados', 
        'empleados_vacaciones': 'En Vacaciones Ahora',
        'porcentaje_vacaciones': 'Porcentaje Actual (%)',
        'Cantidad Solicitudes': 'Total Solicitudes',
        'Días Promedio': 'Días Promedio'
    }
    
    consolidated_table = consolidated_table[list(final_columns.keys())].rename(columns=final_columns)
    
    st.dataframe(consolidated_table, use_container_width=True)


def render_current_vacations_tab(filtered_data, current_vacations):
    today = pd.Timestamp.now()
    st.subheader("🌴 Empleados Actualmente en Vacaciones")
    st.write(f"**Fecha actual:** {today.strftime('%Y-%m-%d')}")
    
    if current_vacations.empty:
        st.info("😊 No hay empleados actualmente en vacaciones")
        
        st.subheader("Próximas Vacaciones")
        upcoming_vacations = filtered_data[
            (filtered_data["Fecha inicio"] > today) &
            (filtered_data["Aprobado"] == "Sí")
        ].sort_values("Fecha inicio").head(10)
        
        if not upcoming_vacations.empty:
            upcoming_display = upcoming_vacations[['Nombre', 'Departamento', 'Fecha inicio', 'Fecha fin', 'Días']].copy()
            st.dataframe(upcoming_display, use_container_width=True)
        else:
            st.info("No hay vacaciones programadas próximamente")
        return
    
    remaining_days = (current_vacations['Fecha fin'] - today).dt.days
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total en vacaciones", len(current_vacations))
    with col2:
        st.metric("Departamentos afectados", current_vacations['Departamento'].nunique())
    with col3:
        st.metric("Días restantes promedio", f"{remaining_days.mean():.0f}")
    
    st.subheader("Detalle de Empleados")
    employee_details = current_vacations.copy()
    employee_details['Días restantes'] = remaining_days
    employee_details = employee_details[['Nombre', 'Departamento', 'Fecha inicio', 'Fecha fin', 'Días', 'Días restantes']]
    st.dataframe(employee_details, use_container_width=True)
    
    st.subheader("Filtrar por Departamento")
    dept_options = ['-'] + sorted(current_vacations['Departamento'].unique().tolist())
    selected_department = st.selectbox("Selecciona un departamento", dept_options)
    
    if selected_department != '-':
        filtered_employees = current_vacations[current_vacations['Departamento'] == selected_department]
        st.write(f"**Empleados de {selected_department} en vacaciones:**")
        st.dataframe(
            filtered_employees[['Nombre', 'Fecha inicio', 'Fecha fin', 'Días']], 
            use_container_width=True
        )

def main():
    
    # Sidebar filters
    st.sidebar.header("Filtros")
    
    uploaded_file = st.sidebar.file_uploader("Subir archivo Excel", type=["xlsx"])
    data = data_loader(uploaded_file)
    
    # Optimize filter widgets
    selected_departments = st.sidebar.multiselect(
        "Departamento",
        options=data["Departamento"].cat.categories.tolist(),
        default=data["Departamento"].cat.categories.tolist()
    )
    selected_approval_status = st.sidebar.multiselect(
        "Estado aprobación",
        options=data["Aprobado"].cat.categories.tolist(),
        default=data["Aprobado"].cat.categories.tolist()
    )
    date_range = st.sidebar.date_input(
        "Rango de fechas",
        [data["Fecha inicio"].min(), data["Fecha fin"].max()]
    )
    
    # Apply filters and calculations
    filtered_data = get_filtered_data(data, selected_departments, selected_approval_status, date_range)
    current_vacations = get_current_vacations(filtered_data)
    total_emp, avg_days, approved_pct = calculate_summary_metrics(filtered_data)
    
    # Render main interface
    st.title("📅 Visualización de Vacaciones")
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    
    render_summary_cards(total_emp, avg_days, approved_pct, len(current_vacations))
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
    
    # Render tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Tabla/Gantt",
        "📊 Estadísticas por Semana",
        "🏢 Dashboard Departamentos", 
        "🌴 Empleados en Vacaciones",
    ])
    
    with tab1:
        view_type = st.radio("Selecciona vista", ["Tabla", "Diagrama de Gantt"], horizontal=True)
        if view_type == "Tabla":
            render_table_view(filtered_data)
        else:
            render_gantt_view(filtered_data)
    
    with tab2:
        render_weekly_stats(filtered_data)
    
    with tab3:
        render_department_dashboard(data, current_vacations)
    
    with tab4:
        render_current_vacations_tab(filtered_data, current_vacations)

if __name__ == "__main__":
    main()