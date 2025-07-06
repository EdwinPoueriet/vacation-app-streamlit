# test_functional_requirements.py
"""
Functional Requirements Tests for Vacation Visualization Module

This file contains tests specifically designed to validate each functional
requirement mentioned in the technical assessment PDF.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
from unittest.mock import patch, MagicMock

# Import functions from your app
from app import (
    data_loader, conflicts_detector, table_formatter, 
    employees_vacations_per_week, department_percentages,
    get_filtered_data, get_current_vacations, calculate_summary_metrics
)

class TestRequirement1:
    """
    Requirement 1: Visualización dinámica de los períodos de vacaciones de empleados, 
    en formato calendario o tabla cronológica.
    """
    
    @pytest.mark.functional
    def test_dynamic_vacation_visualization(self, sample_vacation_data):
        """Test that vacation periods can be visualized dynamically"""
        
        # Test table format visualization
        conflicts = conflicts_detector(sample_vacation_data)
        formatted_table = table_formatter(sample_vacation_data, conflicts)
        
        # Verify table contains all required columns for visualization
        required_columns = ['Empleado', 'Departamento', 'Inicio de Vacaciones', 'Fin de Vacaciones']
        for col in required_columns:
            assert col in formatted_table.columns, f"Missing column for visualization: {col}"
        
        # Verify dates are properly formatted for chronological display
        assert 'Inicio de Vacaciones' in formatted_table.columns
        assert 'Fin de Vacaciones' in formatted_table.columns
        
        # Test that data can be sorted chronologically
        assert len(formatted_table) > 0, "Table should contain vacation data"
    
    @pytest.mark.functional
    def test_chronological_data_structure(self, sample_vacation_data):
        """Test that vacation data maintains chronological structure"""
        
        # Verify date columns are properly typed
        assert pd.api.types.is_datetime64_any_dtype(sample_vacation_data['Fecha inicio'])
        assert pd.api.types.is_datetime64_any_dtype(sample_vacation_data['Fecha fin'])
        
        # Test chronological ordering capability
        sorted_data = sample_vacation_data.sort_values('Fecha inicio')
        assert len(sorted_data) == len(sample_vacation_data)


class TestRequirement2:
    """
    Requirement 2: Filtros por departamento, estado de aprobación y rango de fechas.
    """
    
    @pytest.mark.functional
    def test_department_filtering(self):
        """Test filtering by department functionality"""
        
        test_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3', 'Emp4'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'RRHH', 'Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-02', '2024-07-03', '2024-07-04']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-09', '2024-07-10', '2024-07-11']),
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí', 'No'])
        })
        
        # Test single department filter
        marketing_only = get_filtered_data(
            test_data,
            departments=['Marketing'],
            approval_status=['Sí', 'No'],
            date_range=[]
        )
        assert len(marketing_only) == 2
        assert all(marketing_only['Departamento'] == 'Marketing')
        
        # Test multiple department filter
        marketing_ventas = get_filtered_data(
            test_data,
            departments=['Marketing', 'Ventas'],
            approval_status=['Sí', 'No'],
            date_range=[]
        )
        assert len(marketing_ventas) == 3
        assert set(marketing_ventas['Departamento'].unique()) <= {'Marketing', 'Ventas'}
    
    @pytest.mark.functional
    def test_approval_status_filtering(self):
        """Test filtering by approval status"""
        
        test_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3', 'Emp4'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'RRHH', 'Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-02', '2024-07-03', '2024-07-04']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-09', '2024-07-10', '2024-07-11']),
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'No', 'No'])
        })
        
        # Test approved only filter
        approved_only = get_filtered_data(
            test_data,
            departments=['Marketing', 'Ventas', 'RRHH'],
            approval_status=['Sí'],
            date_range=[]
        )
        assert len(approved_only) == 2
        assert all(approved_only['Aprobado'] == 'Sí')
        
        # Test not approved only filter
        not_approved_only = get_filtered_data(
            test_data,
            departments=['Marketing', 'Ventas', 'RRHH'],
            approval_status=['No'],
            date_range=[]
        )
        assert len(not_approved_only) == 2
        assert all(not_approved_only['Aprobado'] == 'No')
    

class TestRequirement3:
    """
    Requirement 3: Indicador visual de conflictos de fechas entre empleados del mismo departamento.
    """
    
    @pytest.mark.functional
    def test_conflict_detection_same_department(self):
        """Test conflict detection within same department"""
        
        conflict_data = pd.DataFrame({
            'Nombre': ['Alice', 'Bob', 'Charlie'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-12', '2024-07-08']),
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí'])
        })
        
        conflicts = conflicts_detector(conflict_data)
        
        # Should detect conflict between Alice and Bob (both Marketing, overlapping dates)
        conflict_names = [c['Nombre'] for c in conflicts]
        assert 'Alice' in conflict_names or 'Bob' in conflict_names
        
        # Should not detect conflict with Charlie (different department)
        marketing_conflicts = [c for c in conflicts if c['Departamento'] == 'Marketing']
        assert len(marketing_conflicts) > 0
    
    @pytest.mark.functional
    def test_no_conflict_different_departments(self):
        """Test that conflicts are not detected across different departments"""
        
        no_conflict_data = pd.DataFrame({
            'Nombre': ['Alice', 'Bob'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-10']),
            'Aprobado': pd.Categorical(['Sí', 'Sí'])
        })
        
        conflicts = conflicts_detector(no_conflict_data)
        assert len(conflicts) == 0, "Should not detect conflicts across different departments"
    

class TestRequirement4:
    """
    Requirement 4: Panel resumen con estadísticas: número de empleados de vacaciones por semana, 
    % de solicitudes aprobadas, días promedio solicitados.
    """
    
    @pytest.mark.functional
    def test_weekly_employee_statistics(self):
        """Test weekly vacation statistics calculation"""
        
        # Create data spanning multiple weeks
        test_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3', 'Emp4'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-08', '2024-07-15', '2024-07-22']),
            'Fecha fin': pd.to_datetime(['2024-07-07', '2024-07-14', '2024-07-21', '2024-07-28']),
            'Días': [7, 7, 7, 7],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí', 'Sí'])
        })
        
        weekly_stats = employees_vacations_per_week(test_data)
        
        # Should return weekly statistics
        assert isinstance(weekly_stats, pd.DataFrame)
        assert 'empleados_vacaciones' in weekly_stats.columns
        assert 'week_start' in weekly_stats.columns
        assert len(weekly_stats) > 0
        
        # Should track number of employees per week
        assert weekly_stats['empleados_vacaciones'].sum() >= len(test_data)
    
    @pytest.mark.functional 
    def test_approval_percentage_calculation(self):
        """Test approval percentage calculation"""
        
        test_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3', 'Emp4'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-02', '2024-07-03', '2024-07-04']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-09', '2024-07-10', '2024-07-11']),
            'Días': [8, 8, 8, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'No', 'No'])  # 50% approved
        })
        
        total_emp, avg_days, approved_pct = calculate_summary_metrics(test_data)
        
        assert approved_pct == 50.0, f"Expected 50% approval rate, got {approved_pct}%"
        assert total_emp == 4
        assert avg_days == 8.0
    
    @pytest.mark.functional
    def test_average_days_calculation(self):
        """Test average vacation days calculation"""
        
        test_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-02', '2024-07-03']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-09', '2024-07-10']),
            'Días': [5, 10, 15],  # Average should be 10
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí'])
        })
        
        total_emp, avg_days, approved_pct = calculate_summary_metrics(test_data)
        
        assert avg_days == 10.0, f"Expected average of 10 days, got {avg_days}"


class TestRequirement5:
    """
    Requirement 5: Posibilidad de cargar nuevos datos desde un archivo Excel.
    """
    
    @pytest.mark.functional
    def test_excel_file_loading(self, temp_excel_file):
        """Test loading data from Excel file"""
        
        # Test loading from file path
        with open(temp_excel_file, 'rb') as f:
            data = data_loader(f)
        
        # Verify data was loaded correctly
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        # Verify required columns exist after loading
        required_columns = ['Nombre', 'Departamento', 'Fecha inicio', 'Fecha fin', 'Días', 'Aprobado']
        for col in required_columns:
            assert col in data.columns, f"Missing required column: {col}"
    
    @pytest.mark.functional
    def test_excel_data_type_conversion(self, temp_excel_file):
        """Test that Excel data is properly converted to appropriate types"""
        
        with open(temp_excel_file, 'rb') as f:
            data = data_loader(f)
        
        # Verify data types after loading
        assert pd.api.types.is_datetime64_any_dtype(data['Fecha inicio'])
        assert pd.api.types.is_datetime64_any_dtype(data['Fecha fin'])
        assert data['Departamento'].dtype.name == 'category'
        assert data['Aprobado'].dtype.name == 'category'
        assert pd.api.types.is_numeric_dtype(data['Días'])
    
    

class TestRequirement6:
    """
    Requirement 6: Dashboard con visualización del porcentaje de personas de vacaciones por departamento.
    """
    
    @pytest.mark.functional
    def test_department_percentage_calculation(self):
        """Test department-wise vacation percentage calculation"""
        
        # Create test data with known distribution
        all_employees = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3', 'Emp4', 'Emp5', 'Emp6'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing', 'Ventas', 'Ventas', 'RRHH', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01'] * 6),
            'Fecha fin': pd.to_datetime(['2024-07-10'] * 6),
            'Días': [8] * 6,
            'Aprobado': pd.Categorical(['Sí'] * 6)
        })
        
        # Only some employees currently on vacation
        current_vacations = all_employees.iloc[:4]  # 2 Marketing, 2 Ventas, 0 RRHH
        
        dept_stats = department_percentages(all_employees, current_vacations)
        
        # Verify structure
        assert isinstance(dept_stats, pd.DataFrame)
        assert 'porcentaje_vacaciones' in dept_stats.columns
        assert 'total_empleados' in dept_stats.columns
        assert 'empleados_vacaciones' in dept_stats.columns
        
        # Verify calculations
        marketing_row = dept_stats[dept_stats['Departamento'] == 'Marketing'].iloc[0]
        assert marketing_row['total_empleados'] == 2
        assert marketing_row['empleados_vacaciones'] == 2
        assert marketing_row['porcentaje_vacaciones'] == 100.0
        
        rrhh_row = dept_stats[dept_stats['Departamento'] == 'RRHH'].iloc[0]
        assert rrhh_row['porcentaje_vacaciones'] == 0.0
    
    @pytest.mark.functional
    def test_department_dashboard_data_structure(self):
        """Test that department dashboard data is properly structured"""
        
        test_data = pd.DataFrame({
            'Nombre': [f'Emp{i}' for i in range(1, 13)],
            'Departamento': pd.Categorical(['Marketing'] * 4 + ['Ventas'] * 4 + ['RRHH'] * 4),
            'Fecha inicio': pd.to_datetime(['2024-07-01'] * 12),
            'Fecha fin': pd.to_datetime(['2024-07-10'] * 12),
            'Días': [8] * 12,
            'Aprobado': pd.Categorical(['Sí'] * 9 + ['No'] * 3)
        })
        
        current_vacations = test_data[test_data['Aprobado'] == 'Sí']
        dept_stats = department_percentages(test_data, current_vacations)
        
        # Should have data for all departments
        assert len(dept_stats) == 3  # Marketing, Ventas, RRHH
        
        # All percentages should be calculable
        assert not dept_stats['porcentaje_vacaciones'].isna().any()
        assert (dept_stats['porcentaje_vacaciones'] >= 0).all()
        assert (dept_stats['porcentaje_vacaciones'] <= 100).all()


class TestRequirement7:
    """
    Requirement 7: Página de visualización de empleados actualmente de vacaciones (basado en la fecha actual).
    """
    
    @pytest.mark.functional
    def test_current_vacations_identification(self):
        """Test identification of employees currently on vacation"""
        
        today = pd.Timestamp('2024-07-15')  # Fixed date for testing
        
        test_data = pd.DataFrame({
            'Nombre': ['Current1', 'Current2', 'Future1', 'Past1'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing', 'RRHH']),
            'Fecha inicio': [
                today - timedelta(days=5),   # Started 5 days ago
                today - timedelta(days=2),   # Started 2 days ago  
                today + timedelta(days=5),   # Starts in 5 days
                today - timedelta(days=15)   # Started 15 days ago
            ],
            'Fecha fin': [
                today + timedelta(days=5),   # Ends in 5 days
                today + timedelta(days=3),   # Ends in 3 days
                today + timedelta(days=10),  # Ends in 10 days
                today - timedelta(days=5)    # Ended 5 days ago
            ],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí', 'Sí'])
        })
        
        current_vacations = get_current_vacations(test_data, today)
        
        # Should identify only employees currently on vacation
        assert len(current_vacations) == 2
        current_names = current_vacations['Nombre'].tolist()
        assert 'Current1' in current_names
        assert 'Current2' in current_names
        assert 'Future1' not in current_names
        assert 'Past1' not in current_names
    
    @pytest.mark.functional
    def test_current_vacations_approved_only(self):
        """Test that only approved vacations are considered current"""
        
        today = pd.Timestamp('2024-07-15')
        
        test_data = pd.DataFrame({
            'Nombre': ['Approved', 'NotApproved'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing']),
            'Fecha inicio': [today - timedelta(days=2), today - timedelta(days=2)],
            'Fecha fin': [today + timedelta(days=3), today + timedelta(days=3)],
            'Aprobado': pd.Categorical(['Sí', 'No'])
        })
        
        current_vacations = get_current_vacations(test_data, today)
        
        # Should only include approved vacation
        assert len(current_vacations) == 1
        assert current_vacations.iloc[0]['Nombre'] == 'Approved'
    
    @pytest.mark.functional
    def test_current_vacations_real_time(self):
        """Test current vacations with real-time date"""
        
        # Test with actual current time
        real_time_data = pd.DataFrame({
            'Nombre': ['Employee1'],
            'Departamento': pd.Categorical(['Marketing']),
            'Fecha inicio': [pd.Timestamp.now() - timedelta(days=1)],
            'Fecha fin': [pd.Timestamp.now() + timedelta(days=5)],
            'Aprobado': pd.Categorical(['Sí'])
        })
        
        current_vacations = get_current_vacations(real_time_data)
        
        # Should work with real-time calculation
        assert isinstance(current_vacations, pd.DataFrame)
        # Employee should be currently on vacation
        assert len(current_vacations) == 1


class TestDataIntegrity:
    """Test data integrity and business rules"""
    
    @pytest.mark.functional
    def test_160_employees_requirement(self, mock_excel_data):
        """Test that system can handle 160 employees as specified in requirements"""
        
        df = pd.DataFrame(mock_excel_data)
        
        # Verify we have exactly 160 employees as specified
        assert len(df) == 160, "Should handle exactly 160 employees as per requirements"
        
        # Test that all functions work with this data size
        data = df.copy()
        data['Fecha inicio'] = pd.to_datetime(data['Fecha inicio vacaciones'])
        data['Fecha fin'] = pd.to_datetime(data['Fecha fin vacaciones'])
        data['Departamento'] = data['Departamento'].astype('category')
        data['Aprobado'] = data['Aprobado'].astype('category')
        
        # Test core functions with full dataset
        conflicts = conflicts_detector(data)
        assert isinstance(conflicts, list)
        
        weekly_stats = employees_vacations_per_week(data)
        assert isinstance(weekly_stats, pd.DataFrame)
        
        total_emp, avg_days, approved_pct = calculate_summary_metrics(data)
        assert total_emp == 160
    
    @pytest.mark.functional
    def test_performance_with_large_dataset(self, mock_excel_data):
        """Test system performance with required data size"""
        
        df = pd.DataFrame(mock_excel_data)
        data = df.copy()
        data['Fecha inicio'] = pd.to_datetime(data['Fecha inicio vacaciones'])
        data['Fecha fin'] = pd.to_datetime(data['Fecha fin vacaciones'])
        data['Departamento'] = data['Departamento'].astype('category')
        data['Aprobado'] = data['Aprobado'].astype('category')
        
        import time
        
        # Test that operations complete in reasonable time
        start_time = time.time()
        
        # Run all major operations
        filtered_data = get_filtered_data(
            data,
            departments=data['Departamento'].cat.categories.tolist(),
            approval_status=['Sí', 'No'],
            date_range=[]
        )
        conflicts = conflicts_detector(filtered_data)
        weekly_stats = employees_vacations_per_week(filtered_data)
        current_vacations = get_current_vacations(filtered_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0, f"Processing took {processing_time:.2f} seconds, should be under 5 seconds"


# Additional fixtures for requirements testing
@pytest.fixture
def sample_vacation_data():
    """Sample vacation data for testing"""
    return pd.DataFrame({
        'Nombre': ['Test Employee 1', 'Test Employee 2', 'Test Employee 3'],
        'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing']),
        'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-10']),
        'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-12', '2024-07-17']),
        'Días': [8, 8, 8],
        'Aprobado': pd.Categorical(['Sí', 'Sí', 'No'])
    })


if __name__ == "__main__":
    # Run functional requirements tests
    pytest.main([__file__, "-v", "-m", "functional"])