# test_performance_edge_cases.py
"""
Performance and Edge Case Tests for Vacation Visualization Module

This file contains tests for performance optimization, edge cases,
and stress testing scenarios.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
import time
from unittest.mock import patch

# Import functions from your app
from app import (
    data_loader, conflicts_detector, table_formatter, 
    employees_vacations_per_week, department_percentages,
    get_filtered_data, get_current_vacations, calculate_summary_metrics
)

class TestPerformance:
    """Performance tests for large datasets"""
    
    @pytest.mark.slow
    def test_large_dataset_performance(self):
        """Test performance with large datasets (1000+ employees)"""
        
        # Create large test dataset
        large_data_size = 1000
        large_data = pd.DataFrame({
            'Nombre': [f'Employee_{i}' for i in range(large_data_size)],
            'Departamento': pd.Categorical(np.random.choice(['Marketing', 'Ventas', 'RRHH', 'Finanzas', 'Operaciones'], large_data_size)),
            'Fecha inicio': pd.date_range('2024-01-01', periods=large_data_size, freq='1D'),
            'Fecha fin': pd.date_range('2024-01-08', periods=large_data_size, freq='1D'),
            'Días': np.random.randint(5, 20, large_data_size),
            'Aprobado': pd.Categorical(np.random.choice(['Sí', 'No'], large_data_size, p=[0.8, 0.2]))
        })
        
        start_time = time.time()
        
        # Test core operations with large dataset
        filtered_data = get_filtered_data(
            large_data,
            departments=['Marketing', 'Ventas', 'RRHH'],
            approval_status=['Sí'],
            date_range=[]
        )
        
        conflicts = conflicts_detector(filtered_data)
        weekly_stats = employees_vacations_per_week(filtered_data)
        current_vacations = get_current_vacations(filtered_data)
        total_emp, avg_days, approved_pct = calculate_summary_metrics(filtered_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        assert processing_time < 10.0, f"Large dataset processing took {processing_time:.2f}s, should be under 10s"
        assert len(filtered_data) > 0, "Should return filtered results"
        assert isinstance(conflicts, list), "Should return conflicts list"
        assert isinstance(weekly_stats, pd.DataFrame), "Should return weekly statistics"
    
    @pytest.mark.slow
    def test_conflict_detection_performance(self):
        """Test conflict detection performance with many overlapping vacations"""
        
        # Create scenario with many potential conflicts
        conflict_heavy_data = pd.DataFrame({
            'Nombre': [f'Employee_{i}' for i in range(50)],
            'Departamento': pd.Categorical(['Marketing'] * 50),  # All same department
            'Fecha inicio': pd.to_datetime(['2024-07-01'] * 50),  # All start same day
            'Fecha fin': pd.to_datetime(['2024-07-10'] * 50),    # All end same day
            'Aprobado': pd.Categorical(['Sí'] * 50)
        })
        
        start_time = time.time()
        conflicts = conflicts_detector(conflict_heavy_data)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should detect conflicts efficiently even with many overlaps
        assert processing_time < 5.0, f"Conflict detection took {processing_time:.2f}s, should be under 5s"
        assert len(conflicts) == 50, "Should detect all employees as having conflicts"
    
    @pytest.mark.slow
    def test_weekly_statistics_performance(self):
        """Test weekly statistics calculation performance"""
        
        # Create data spanning entire year
        year_data = pd.DataFrame({
            'Nombre': [f'Employee_{i}' for i in range(365)],
            'Departamento': pd.Categorical(np.random.choice(['Marketing', 'Ventas', 'RRHH'], 365)),
            'Fecha inicio': pd.date_range('2024-01-01', periods=365, freq='1D'),
            'Fecha fin': pd.date_range('2024-01-08', periods=365, freq='1D'),
            'Días': [7] * 365,
            'Aprobado': pd.Categorical(['Sí'] * 365)
        })
        
        start_time = time.time()
        weekly_stats = employees_vacations_per_week(year_data)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert processing_time < 3.0, f"Weekly stats calculation took {processing_time:.2f}s, should be under 3s"
        assert len(weekly_stats) > 50, "Should generate weekly statistics for full year"


class TestEdgeCases:
    """Edge case testing"""
    
    def test_single_employee_dataset(self):
        """Test handling of dataset with single employee"""
        
        single_employee = pd.DataFrame({
            'Nombre': ['Solo Employee'],
            'Departamento': pd.Categorical(['Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-07-10']),
            'Días': [10],
            'Aprobado': pd.Categorical(['Sí'])
        })
        
        # All functions should work with single employee
        conflicts = conflicts_detector(single_employee)
        assert len(conflicts) == 0  # No conflicts possible with single employee
        
        weekly_stats = employees_vacations_per_week(single_employee)
        assert len(weekly_stats) > 0
        
        total_emp, avg_days, approved_pct = calculate_summary_metrics(single_employee)
        assert total_emp == 1
        assert avg_days == 10.0
        assert approved_pct == 100.0
    
    def test_invalid_date_ranges(self):
        """Test handling of invalid date ranges (end before start)"""
        
        invalid_dates = pd.DataFrame({
            'Nombre': ['Invalid Employee'],
            'Departamento': pd.Categorical(['Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-10']),
            'Fecha fin': pd.to_datetime(['2024-07-01']),  # End before start
            'Días': [10],
            'Aprobado': pd.Categorical(['Sí'])
        })
        
        # Functions should handle invalid dates gracefully
        conflicts = conflicts_detector(invalid_dates)
        assert isinstance(conflicts, list)
        
        weekly_stats = employees_vacations_per_week(invalid_dates)
        assert isinstance(weekly_stats, pd.DataFrame)
    
    def test_extreme_date_ranges(self):
        """Test handling of extreme date ranges"""
        
        extreme_dates = pd.DataFrame({
            'Nombre': ['Past Employee', 'Future Employee', 'Long Vacation Employee'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['1900-01-01', '2100-01-01', '2024-01-01']),
            'Fecha fin': pd.to_datetime(['1900-01-10', '2100-01-10', '2025-01-01']),  # 1 year vacation
            'Días': [10, 10, 365],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí'])
        })
        
        # Should handle extreme dates without errors
        conflicts = conflicts_detector(extreme_dates)
        assert isinstance(conflicts, list)
        
        weekly_stats = employees_vacations_per_week(extreme_dates)
        assert isinstance(weekly_stats, pd.DataFrame)
    
    def test_duplicate_employees(self):
        """Test handling of duplicate employee records"""
        
        duplicate_data = pd.DataFrame({
            'Nombre': ['Employee 1', 'Employee 1', 'Employee 2'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-15', '2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-20', '2024-07-08']),
            'Días': [10, 6, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí'])
        })
        
        # Should handle duplicates (possibly same employee with multiple vacation periods)
        conflicts = conflicts_detector(duplicate_data)
        assert isinstance(conflicts, list)
        
        formatted_table = table_formatter(duplicate_data, conflicts)
        assert isinstance(formatted_table, pd.DataFrame)
    
    def test_missing_values_comprehensive(self):
        """Comprehensive test for missing values in various columns"""
        
        missing_data = pd.DataFrame({
            'Nombre': ['Employee 1', None, 'Employee 3', 'Employee 4'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', None, 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', None, '2024-07-15']),
            'Fecha fin': pd.to_datetime(['2024-07-10', None, '2024-07-20', '2024-07-22']),
            'Días': [10, 8, None, 8],
            'Aprobado': pd.Categorical(['Sí', None, 'No', 'Sí'])
        })
        
        # All functions should handle missing values gracefully
        try:
            conflicts = conflicts_detector(missing_data)
            weekly_stats = employees_vacations_per_week(missing_data)
            current_vacations = get_current_vacations(missing_data)
            total_emp, avg_days, approved_pct = calculate_summary_metrics(missing_data)
            
            # Should not raise exceptions
            assert True, "Functions handled missing values without errors"
        except Exception as e:
            pytest.fail(f"Functions should handle missing values gracefully, but got: {e}")
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters in names"""
        
        unicode_data = pd.DataFrame({
            'Nombre': ['José María', 'François', '李小明', 'Müller', 'O\'Connor'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'RRHH', 'Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-10', '2024-07-15', '2024-07-20']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-12', '2024-07-17', '2024-07-22', '2024-07-27']),
            'Días': [8, 8, 8, 8, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí', 'Sí', 'Sí'])
        })
        
        # Should handle unicode characters without issues
        conflicts = conflicts_detector(unicode_data)
        formatted_table = table_formatter(unicode_data, conflicts)
        
        assert isinstance(formatted_table, pd.DataFrame)
        assert len(formatted_table) == 5
    
    def test_very_large_numbers(self):
        """Test handling of very large numbers in days column"""
        
        large_numbers_data = pd.DataFrame({
            'Nombre': ['Normal Employee', 'Long Vacation Employee', 'Invalid Days Employee'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'RRHH']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-01', '2024-07-01']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-10', '2024-07-10']),
            'Días': [10, 999999, -5],  # Normal, very large, negative
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí'])
        })
        
        # Should handle extreme values gracefully
        total_emp, avg_days, approved_pct = calculate_summary_metrics(large_numbers_data)
        
        assert isinstance(avg_days, float)
        assert not np.isnan(avg_days) or avg_days >= 0


class TestDataValidation:
    """Data validation and business rule tests"""
    
    def test_department_consistency(self):
        """Test that department data remains consistent throughout processing"""
        
        test_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2', 'Emp3'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas', 'Marketing']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-10']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-12', '2024-07-17']),
            'Días': [8, 8, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí'])
        })
        
        # Original departments
        original_depts = set(test_data['Departamento'].cat.categories)
        
        # After filtering
        filtered_data = get_filtered_data(
            test_data,
            departments=['Marketing', 'Ventas'],
            approval_status=['Sí'],
            date_range=[]
        )
        
        filtered_depts = set(filtered_data['Departamento'].unique())
        
        # Should maintain department consistency
        assert filtered_depts.issubset(original_depts)
    
    def test_approval_status_validation(self):
        """Test that approval status values are valid"""
        
        valid_data = pd.DataFrame({
            'Nombre': ['Emp1', 'Emp2'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-12']),
            'Días': [8, 8],
            'Aprobado': pd.Categorical(['Sí', 'No'])
        })
        
        # All approval statuses should be valid
        valid_statuses = {'Sí', 'No'}
        actual_statuses = set(valid_data['Aprobado'].cat.categories)
        
        assert actual_statuses.issubset(valid_statuses), f"Invalid approval statuses: {actual_statuses - valid_statuses}"
    
    def test_date_logic_validation(self):
        """Test business logic around dates"""
        
        test_data = pd.DataFrame({
            'Nombre': ['Valid Employee', 'Same Day Employee'],
            'Departamento': pd.Categorical(['Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05']),
            'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-05']),  # Same start/end date
            'Días': [10, 1],
            'Aprobado': pd.Categorical(['Sí', 'Sí'])
        })
        
        # Should handle same-day vacations
        conflicts = conflicts_detector(test_data)
        weekly_stats = employees_vacations_per_week(test_data)
        
        assert isinstance(conflicts, list)
        assert isinstance(weekly_stats, pd.DataFrame)


class TestMemoryUsage:
    """Memory usage and resource management tests"""
    
    @pytest.mark.slow
    def test_memory_efficiency_large_dataset(self):
        """Test memory efficiency with large datasets"""
        
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        large_data = pd.DataFrame({
            'Nombre': [f'Employee_{i}' for i in range(5000)],
            'Departamento': pd.Categorical(np.random.choice(['Marketing', 'Ventas', 'RRHH'], 5000)),
            'Fecha inicio': pd.date_range('2024-01-01', periods=5000, freq='1H'),
            'Fecha fin': pd.date_range('2024-01-01', periods=5000, freq='1H') + timedelta(days=7),
            'Días': np.random.randint(5, 15, 5000),
            'Aprobado': pd.Categorical(np.random.choice(['Sí', 'No'], 5000))
        })
        
        # Process data
        filtered_data = get_filtered_data(
            large_data,
            departments=['Marketing', 'Ventas'],
            approval_status=['Sí'],
            date_range=[]
        )
        
        conflicts = conflicts_detector(filtered_data)
        weekly_stats = employees_vacations_per_week(filtered_data)
        
        # Check memory usage after processing
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (adjust threshold as needed)
        assert memory_increase < 500, f"Memory usage increased by {memory_increase:.2f} MB, should be under 500 MB"


class TestConcurrency:
    """Concurrency and thread safety tests"""
    
    def test_function_thread_safety(self):
        """Test that functions are thread-safe"""
        
        import threading
        import queue
        
        test_data = pd.DataFrame({
            'Nombre': [f'Employee_{i}' for i in range(100)],
            'Departamento': pd.Categorical(np.random.choice(['Marketing', 'Ventas', 'RRHH'], 100)),
            'Fecha inicio': pd.date_range('2024-07-01', periods=100, freq='1D'),
            'Fecha fin': pd.date_range('2024-07-08', periods=100, freq='1D'),
            'Días': [7] * 100,
            'Aprobado': pd.Categorical(['Sí'] * 100)
        })
        
        results_queue = queue.Queue()
        
        def worker():
            try:
                conflicts = conflicts_detector(test_data)
                weekly_stats = employees_vacations_per_week(test_data)
                current_vacations = get_current_vacations(test_data)
                results_queue.put(('success', len(conflicts), len(weekly_stats), len(current_vacations)))
            except Exception as e:
                results_queue.put(('error', str(e)))
        
        # Run multiple threads concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        while not results_queue.empty():
            result = results_queue.get()
            assert result[0] == 'success', f"Thread failed with error: {result[1] if result[0] == 'error' else 'Unknown'}"


class TestErrorRecovery:
    """Error recovery and resilience tests"""
    
    def test_partial_data_corruption_recovery(self):
        """Test recovery from partial data corruption"""
        
        # Create data with some corrupted entries
        corrupted_data = pd.DataFrame({
            'Nombre': ['Good Employee', '', 'Another Good Employee'],
            'Departamento': pd.Categorical(['Marketing', 'Marketing', 'Ventas']),
            'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-10']),
            'Fecha fin': pd.to_datetime(['2024-07-08', '2024-07-12', '2024-07-17']),
            'Días': [8, 8, 8],
            'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí'])
        })
        
        # Should process non-corrupted data successfully
        try:
            conflicts = conflicts_detector(corrupted_data)
            weekly_stats = employees_vacations_per_week(corrupted_data)
            
            # Should return results for valid data
            assert isinstance(conflicts, list)
            assert isinstance(weekly_stats, pd.DataFrame)
            
        except Exception as e:
            pytest.fail(f"Should handle partial corruption gracefully: {e}")
    
    def test_network_interruption_simulation(self):
        """Simulate network interruption during file loading"""
        
        # This would be more relevant for S3 integration
        # For now, test file corruption scenario
        
        corrupt_data = b"This is not valid Excel data"
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_file.write(corrupt_data)
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                with pytest.raises(Exception):  # Should raise some kind of exception
                    data_loader(f)
        finally:
            os.unlink(temp_file.name)


if __name__ == "__main__":
    # Run performance and edge case tests
    pytest.main([__file__, "-v", "--tb=short"])