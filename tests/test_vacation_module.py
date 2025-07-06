import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
from unittest.mock import patch, MagicMock
import streamlit as st

# Import functions from your app
from app import (
    data_loader, conflicts_detector, table_formatter, 
    employees_vacations_per_week, department_percentages,
    get_filtered_data, get_current_vacations, calculate_summary_metrics
)

class TestDataLoader:
    """Test data loading functionality"""
    
    def setup_method(self):
        """Setup test data"""
        self.test_data = {
            'ID': [1, 2, 3, 4, 5],
            'Nombre': ['Juan Pérez', 'María García', 'Carlos López', 'Ana Martín', 'Luis Rodríguez'],
            'Departamento': ['Marketing', 'Ventas', 'Marketing', 'RRHH', 'Ventas'],
            'Fecha inicio vacaciones': ['2024-07-01', '2024-07-05', '2024-07-03', '2024-07-10', '2024-07-15'],
            'Fecha fin vacaciones': ['2024-07-10', '2024-07-12', '2024-07-08', '2024-07-17', '2024-07-22'],
            'Días': [10, 8, 6, 8, 8],
            'Aprobado': ['Sí', 'Sí', 'No', 'Sí', 'Sí']
        }
    
    def create_test_excel(self, data=None):
        """Create a temporary Excel file for testing"""
        if data is None:
            data = self.test_data
        
        df = pd.DataFrame(data)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        df.to_excel(temp_file.name, index=False)
        return temp_file.name
    
    def test_data_loader_with_file(self):
        """Test data loading from uploaded file"""
        temp_file = self.create_test_excel()
        
        try:
            # Mock uploaded file
            with open(temp_file, 'rb') as f:
                data = data_loader(f)
            
            # Verify data types and structure
            assert isinstance(data, pd.DataFrame)
            assert len(data) == 5
            assert 'Fecha inicio' in data.columns
            assert 'Fecha fin' in data.columns
            assert pd.api.types.is_datetime64_any_dtype(data['Fecha inicio'])
            assert pd.api.types.is_datetime64_any_dtype(data['Fecha fin'])
            assert data['Departamento'].dtype.name == 'category'
            assert data['Aprobado'].dtype.name == 'category'
            
        finally:
            os.unlink(temp_file)
    
    def test_data_loader_invalid_data_types(self):
        """Test data loader with invalid data types"""
        invalid_data = self.test_data.copy()
        invalid_data['Días'] = ['invalid', 'data', '10', 'test', '5']
        
        temp_file = self.create_test_excel(invalid_data)
        
        try:
            with open(temp_file, 'rb') as f:
                data = data_loader(f)
            
            # Should handle invalid numeric data gracefully
            assert data['Días'].isna().sum() > 0  # Some values should be NaN
            
        finally:
            os.unlink(temp_file)
    
    def test_data_loader_missing_columns(self):
        """Test data loader with missing required columns"""
        incomplete_data = {
            'ID': [1, 2],
            'Nombre': ['Test 1', 'Test 2']
            # Missing required columns
        }
        
        temp_file = self.create_test_excel(incomplete_data)
        
        try:
            with open(temp_file, 'rb') as f:
                with pytest.raises(KeyError):
                    data_loader(f)
        finally:
            os.unlink(temp_file)


class TestConflictDetection:
    """Test conflict detection functionality - Requirement 3"""
    
    def setup_method(self):
        """Setup test data with known conflicts"""
        self.conflict_data = pd.DataFrame({
            'Nombre': ['Employee A', 'Employee B', 'Employee C', 'Employee D'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing', 'Ventas', 'Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-01', '2024-07-03']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-12', '2024-07-08', '2024-07-06']),
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí', 'Sí'])
        })
    
    def test_conflicts_detector_with_conflicts(self):
        """Test conflict detection when conflicts exist"""
        conflicts = conflicts_detector(self.conflict_data)
        
        # Should detect conflicts in Marketing department
        assert len(conflicts) > 0
        
        # Check that conflicting employees are identified
        conflict_names = [c['Nombre'] for c in conflicts]
        assert 'Employee A' in conflict_names or 'Employee B' in conflict_names
    
    def test_conflicts_detector_no_conflicts(self):
        """Test conflict detection with no overlapping dates"""
        no_conflict_data = pd.DataFrame({
            'Nombre': ['Employee A', 'Employee B'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-15']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-20']),
            'Aprobado': pd.Categorical(['Sí', 'Sí'])
        })
        
        conflicts = conflicts_detector(no_conflict_data)
        assert len(conflicts) == 0
    
    def test_conflicts_detector_different_departments(self):
        """Test that conflicts are only detected within same department"""
        different_dept_data = pd.DataFrame({
            'Nombre': ['Employee A', 'Employee B'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-10']),
            'Aprobado': pd.Categorical(['Sí', 'Sí'])
        })
        
        conflicts = conflicts_detector(different_dept_data)
        assert len(conflicts) == 0
    
    def test_conflicts_detector_unapproved_vacations(self):
        """Test that only approved vacations are considered for conflicts"""
        unapproved_data = pd.DataFrame({
            'Nombre': ['Employee A', 'Employee B'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-10']),
            'Aprobado': pd.Categorical(['No', 'No'])
        })
        
        conflicts = conflicts_detector(unapproved_data)
        assert len(conflicts) == 0


class TestFiltering:
    """Test filtering functionality - Requirement 2"""
    
    def setup_method(self):
        """Setup test data for filtering"""
        self.filter_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3', 'Emp4'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-10', '2024-07-15']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-12', '2024-07-17', '2024-07-22']),
            'Aprobado': pd.Categorical(['Sí', 'No', 'Sí', 'Sí'])
        })
    
    def test_filter_by_department(self):
        """Test filtering by department"""
        filtered = get_filtered_data(
            self.filter_data, 
            departments=['Marketing'], 
            approval_status=['Sí', 'No'],
            date_range=[]
        )
        
        assert len(filtered) == 2
        assert all(filtered['Departamento'] == 'Marketing')
    
    def test_filter_by_approval_status(self):
        """Test filtering by approval status"""
        filtered = get_filtered_data(
            self.filter_data,
            departments=['Marketing', 'Ventas', 'RRHH'],
            approval_status=['Sí'],
            date_range=[]
        )
        
        assert len(filtered) == 3
        assert all(filtered['Aprobado'] == 'Sí')
    
    def test_combined_filters(self):
        """Test multiple filters applied together"""
        filtered = get_filtered_data(
            self.filter_data,
            departments=['Marketing'],
            approval_status=['Sí'],
            date_range=[datetime(2024, 7, 1), datetime(2024, 7, 15)]
        )
        
        assert len(filtered) == 1
        assert filtered.iloc[0]['Nombre'] == 'Emp1'


class TestStatistics:
    """Test statistics calculations - Requirement 4"""
    
    def setup_method(self):
        """Setup test data for statistics"""
        self.stats_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3', 'Emp4'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-10', '2024-07-15']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-12', '2024-07-17', '2024-07-22']),
            'Días': [10, 8, 8, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'No', 'Sí'])
        })
    
    def test_calculate_summary_metrics(self):
        """Test summary metrics calculation"""
        total_emp, avg_days, approved_pct = calculate_summary_metrics(self.stats_data)
        
        assert total_emp == 4
        assert avg_days == 8.5  # (10 + 8 + 8 + 8) / 4
        assert approved_pct == 75.0  # 3 out of 4 approved
    
    def test_calculate_summary_metrics_empty_data(self):
        """Test summary metrics with empty data"""
        empty_data = pd.DataFrame()
        total_emp, avg_days, approved_pct = calculate_summary_metrics(empty_data)
        
        assert total_emp == 0
        assert avg_days == 0.0
        assert approved_pct == 0.0
    
    def test_employees_vacations_per_week(self):
        """Test weekly vacation statistics"""
        weekly_stats = employees_vacations_per_week(self.stats_data)
        
        assert isinstance(weekly_stats, pd.DataFrame)
        assert 'empleados_vacaciones' in weekly_stats.columns
        assert 'week_start' in weekly_stats.columns
        assert len(weekly_stats) > 0
    
    def test_department_percentages(self):
        """Test department percentage calculations"""
        current_vacations = self.stats_data[self.stats_data['Aprobado'] == 'Sí']
        dept_stats = department_percentages(self.stats_data, current_vacations)
        
        assert isinstance(dept_stats, pd.DataFrame)
        assert 'porcentaje_vacaciones' in dept_stats.columns
        assert 'total_empleados' in dept_stats.columns
        assert 'empleados_vacaciones' in dept_stats.columns


class TestCurrentVacations:
    """Test current vacations functionality - Requirement 7"""
    
    def setup_method(self):
        """Setup test data with current and future vacations"""
        today = pd.Timestamp.now()
        self.current_vacation_data = pd.DataFrame({
            'Nombre': ['Current1', 'Current2', 'Future1', 'Past1'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing', 'RRHH']),
            'Fecha inicio': [
                today - timedelta(days=2),
                today - timedelta(days=1),
                today + timedelta(days=5),
                today - timedelta(days=10)
            ],
            'Fecha fin': [
                today + timedelta(days=3),
                today + timedelta(days=2),
                today + timedelta(days=10),
                today - timedelta(days=5)
            ],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí', 'Sí'])
        })
    
    def test_get_current_vacations(self):
        """Test identification of current vacations"""
        today = pd.Timestamp.now()
        current = get_current_vacations(self.current_vacation_data, today)
        
        # Should only include employees currently on vacation
        assert len(current) == 2
        current_names = current['Nombre'].tolist()
        assert 'Current1' in current_names
        assert 'Current2' in current_names
        assert 'Future1' not in current_names
        assert 'Past1' not in current_names
    
    def test_get_current_vacations_specific_date(self):
        """Test current vacations for a specific date"""
        test_date = pd.Timestamp('2024-07-01')
        
        # Create data relative to test date
        test_data = pd.DataFrame({
            'Nombre': ['Test1', 'Test2'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas']),
            'Fecha inicio': [
                test_date - timedelta(days=2),
                test_date + timedelta(days=1)
            ],
            'Fecha fin': [
                test_date + timedelta(days=2),
                test_date + timedelta(days=5)
            ],
            'Aprobado': pd.Categorical(['Sí', 'Sí'])
        })
        
        current = get_current_vacations(test_data, test_date)
        assert len(current) == 1
        assert current.iloc[0]['Nombre'] == 'Test1'


class TestTableFormatting:
    """Test table formatting and visualization - Requirement 1"""
    
    def setup_method(self):
        """Setup test data for table formatting"""
        self.table_data = pd.DataFrame({
            'Nombre': ['Employee1', 'Employee2'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-12']),
            'Días': [10, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí'])
        })
    
    def test_table_formatter(self):
        """Test table formatting functionality"""
        conflicts = conflicts_detector(self.table_data)
        formatted_table = table_formatter(self.table_data, conflicts)
        
        assert isinstance(formatted_table, pd.DataFrame)
        assert 'Empleado' in formatted_table.columns
        assert 'Departamento' in formatted_table.columns
        assert 'Inicio de Vacaciones' in formatted_table.columns
        assert 'Fin de Vacaciones' in formatted_table.columns
        assert '⚠️' in formatted_table.columns
    
    def test_table_formatter_empty_data(self):
        """Test table formatting with empty data"""
        empty_data = pd.DataFrame()
        conflicts = []
        formatted_table = table_formatter(empty_data, conflicts)
        
        assert isinstance(formatted_table, pd.DataFrame)
        assert len(formatted_table) == 0


class TestDashboardRequirements:
    """Test dashboard functionality - Requirement 6"""
    
    def setup_method(self):
        """Setup test data for dashboard testing"""
        self.dashboard_data = pd.DataFrame({
            'Nombre': [f'Emp{i}' for i in range(1, 11)],
            'Departamento': pd.Categorical(['Marketing'] * 4 + ['Ventas'] * 3 + ['RRHH'] * 3),
            'Fecha inicio': pd.to_datetime(['2024-07-01'] * 10),
            'Fecha fin': pd.to_datetime(['2024-07-10'] * 10),
            'Días': [8] * 10,
            'Aprobado': pd.Categorical(['Sí'] * 8 + ['No'] * 2)
        })
    
    def test_department_dashboard_calculations(self):
        """Test department-wise percentage calculations"""
        current_vacations = self.dashboard_data[self.dashboard_data['Aprobado'] == 'Sí']
        dept_stats = department_percentages(self.dashboard_data, current_vacations)
        
        # Verify department statistics
        marketing_stats = dept_stats[dept_stats['Departamento'] == 'Marketing']
        assert len(marketing_stats) == 1
        assert marketing_stats.iloc[0]['total_empleados'] == 4
        assert marketing_stats.iloc[0]['empleados_vacaciones'] == 4
        assert marketing_stats.iloc[0]['porcentaje_vacaciones'] == 100.0


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_date_handling(self):
        """Test handling of invalid dates"""
        invalid_data = pd.DataFrame({
            'Nombre': ['Test'],
            'Departamento': pd.Categorical(['Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-06-01']),  # End before start
            'Días': [10],
            'Aprobado': pd.Categorical(['Sí'])
        })
        
        # Functions should handle invalid date ranges gracefully
        conflicts = conflicts_detector(invalid_data)
        assert isinstance(conflicts, list)
    
    def test_missing_values_handling(self):
        """Test handling of missing values in data"""
        data_with_nulls = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', None],
            'Departamento': pd.Categorical(['Marketing', None, 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', None]),
            'Fecha fin': pd.to_datetime(['2024-07-10', None, '2024-07-15']),
            'Días': [10, None, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí', None])
        })
        
        # Functions should handle missing values without crashing
        total_emp, avg_days, approved_pct = calculate_summary_metrics(data_with_nulls)
        assert isinstance(total_emp, int)
        assert isinstance(avg_days, float)
        assert isinstance(approved_pct, float)


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def setup_method(self):
        """Setup comprehensive test data"""
        self.integration_data = pd.DataFrame({
            'ID': range(1, 21),
            'Nombre': [f'Employee_{i}' for i in range(1, 21)],
            'Departamento': pd.Categorical(['Marketing'] * 8 + ['Ventas'] * 7 + ['RRHH'] * 5),
            'Fecha inicio vacaciones': pd.date_range('2024-07-01', periods=20, freq='2D'),
            'Fecha fin vacaciones': pd.date_range('2024-07-08', periods=20, freq='2D'),
            'Días': np.random.randint(5, 15, 20),
            'Aprobado': pd.Categorical(['Sí'] * 15 + ['No'] * 5)
        })
    

# Pytest configuration and fixtures
@pytest.fixture
def sample_vacation_data():
    """Fixture providing sample vacation data"""
    return pd.DataFrame({
        'Nombre': ['Test Employee 1', 'Test Employee 2', 'Test Employee 3'],
        'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing']),
        'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-10']),
        'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-12', '2024-07-17']),
        'Días': [8, 8, 8],
        'Aprobado': pd.Categorical(['Sí', 'Sí', 'No'])
    })


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])