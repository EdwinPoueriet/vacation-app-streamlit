import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

@pytest.fixture(scope="session")
def mock_excel_data():
    """Session-scoped fixture for mock Excel data"""
    return {
        'ID': range(1, 161),  # 160 employees as per requirements
        'Nombre': [f'Employee_{i}' for i in range(1, 161)],
        'Departamento': np.random.choice(['Marketing', 'Ventas', 'RRHH', 'Finanzas', 'Operaciones'], 160),
        'Fecha inicio vacaciones': pd.date_range('2024-01-01', periods=160, freq='3D'),
        'Fecha fin vacaciones': pd.date_range('2024-01-08', periods=160, freq='3D'),
        'Días': np.random.randint(5, 20, 160),
        'Aprobado': np.random.choice(['Sí', 'No'], 160, p=[0.8, 0.2])
    }

@pytest.fixture
def temp_excel_file(mock_excel_data):
    """Create temporary Excel file for testing"""
    df = pd.DataFrame(mock_excel_data)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(temp_file.name, index=False)
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass

@pytest.fixture
def conflict_test_data():
    """Fixture for testing conflict detection"""
    return pd.DataFrame({
        'Nombre': ['Alice', 'Bob', 'Charlie', 'Diana'],
        'Departamento': pd.Categorical(['Marketing', 'Marketing', 'Ventas', 'Marketing']),
        'Fecha inicio': pd.to_datetime(['2024-07-01', '2024-07-05', '2024-07-01', '2024-07-03']),
        'Fecha fin': pd.to_datetime(['2024-07-10', '2024-07-12', '2024-07-08', '2024-07-06']),
        'Aprobado': pd.Categorical(['Sí', 'Sí', 'Sí', 'Sí'])
    })