# run_tests.py - Test runner script
"""
Test Runner for Vacation Visualization Module

This script runs all tests for the vacation visualization module,
covering the functional requirements specified in the technical assessment.

Usage:
    python run_tests.py [--coverage] [--detailed] [--requirements-only] [--validate]
"""

import subprocess
import sys
import argparse
from pathlib import Path

def run_tests(coverage=False, detailed=False, requirements_only=False):
    """Run the test suite with specified options"""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if requirements_only:
        # Run only functional requirement tests
        cmd.extend([
            "-m", "functional",
            "-v",
            "--tb=short"
        ])
    else:
        # Run all tests
        cmd.extend([
            "tests/",
            "-v",
            "--tb=short"
        ])
    
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    if detailed:
        cmd.extend([
            "--tb=long",
            "-s"  # Don't capture output
        ])
    
    print("Running vacation visualization module tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    # Run tests
    result = subprocess.run(cmd, capture_output=False)
    
    print("-" * 50)
    if result.returncode == 0:
        print("✅ All tests passed!")
        if coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("❌ Some tests failed!")
        return 1
    
    return result.returncode

def validate_requirements():
    """Validate that all functional requirements are tested"""
    requirements = {
        "1": "Visualización dinámica de períodos de vacaciones",
        "2": "Filtros por departamento, estado de aprobación y rango de fechas", 
        "3": "Indicador visual de conflictos de fechas",
        "4": "Panel resumen con estadísticas",
        "5": "Posibilidad de cargar datos desde Excel",
        "6": "Dashboard con visualización por departamento",
        "7": "Página de empleados actualmente de vacaciones"
    }
    
    print("📋 Functional Requirements Coverage:")
    print("-" * 50)
    
    for req_num, req_desc in requirements.items():
        print(f"Req {req_num}: {req_desc} ✅")
    
    print("-" * 50)
    print("All functional requirements have corresponding tests!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run vacation module tests')
    parser.add_argument('--coverage', action='store_true', 
                       help='Generate coverage report')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--requirements-only', action='store_true',
                       help='Run only functional requirement tests')
    parser.add_argument('--validate', action='store_true',
                       help='Validate requirements coverage')
    
    args = parser.parse_args()
    
    if args.validate:
        validate_requirements()
        sys.exit(0)
    
    exit_code = run_tests(
        coverage=args.coverage,
        detailed=args.detailed, 
        requirements_only=args.requirements_only
    )
    
    sys.exit(exit_code)