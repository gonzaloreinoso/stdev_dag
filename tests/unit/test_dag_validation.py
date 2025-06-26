"""
Unit tests for DAG validation and structure.
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from airflow.models import DagBag


class TestDAGValidation:
    """Test DAG validation and structure."""
    
    @pytest.fixture
    def dagbag(self):
        """Create DagBag for testing."""
        # Add the dags directory to sys.path if not already there
        dags_dir = Path(__file__).parent.parent.parent / 'dags'
        if str(dags_dir) not in sys.path:
            sys.path.insert(0, str(dags_dir))
        
        # Set up environment variables that DAG might need
        os.environ.setdefault('AIRFLOW_HOME', str(Path.cwd()))
        
        return DagBag(dag_folder=str(dags_dir), include_examples=False)
    
    def test_dag_loading(self, dagbag):
        """Test that DAGs load without errors."""
        assert len(dagbag.import_errors) == 0, f"DAG import errors: {dagbag.import_errors}"
        assert len(dagbag.dags) > 0, "No DAGs found"
    
    def test_stdev_dag_exists(self, dagbag):
        """Test that the stdev calculation DAG exists."""
        dag_id = 'stdev_calculation_pipeline'
        assert dag_id in dagbag.dags, f"DAG {dag_id} not found in DagBag"
        
        dag = dagbag.get_dag(dag_id)
        assert dag is not None
        assert dag.dag_id == dag_id
    
    def test_dag_structure(self, dagbag):
        """Test DAG structure and tasks."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        # Expected tasks
        expected_tasks = [
            'extract_and_validate_data',
            'load_raw_data_to_postgres',
            'calculate_standard_deviations',
            'save_results_to_postgres',
            'cleanup_temp_files'
        ]
        
        actual_tasks = list(dag.task_dict.keys())
        
        for task_id in expected_tasks:
            assert task_id in actual_tasks, f"Task {task_id} not found in DAG"
    
    def test_dag_schedule_interval(self, dagbag):
        """Test DAG schedule interval."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        assert dag.schedule_interval == timedelta(hours=1), \
            f"Expected hourly schedule, got {dag.schedule_interval}"
    
    def test_dag_default_args(self, dagbag):
        """Test DAG default arguments."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        default_args = dag.default_args
        
        # Check required default args
        assert 'owner' in default_args
        assert 'depends_on_past' in default_args
        assert 'start_date' in default_args
        assert 'retries' in default_args
        
        # Check specific values
        assert default_args['depends_on_past'] is False
        assert isinstance(default_args['start_date'], datetime)
        assert default_args['retries'] >= 0
    
    def test_dag_no_cycles(self, dagbag):
        """Test that DAG has no cycles."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        # Simple cycle check by verifying task dependencies
        visited = set()
        
        def has_cycle(task, path):
            if task.task_id in path:
                return True
            if task.task_id in visited:
                return False
            
            visited.add(task.task_id)
            for downstream_task in task.downstream_list:
                if has_cycle(downstream_task, path | {task.task_id}):
                    return True
            return False
        
        for task in dag.tasks:
            assert not has_cycle(task, set()), f"Cycle detected involving task {task.task_id}"
    
    def test_task_dependencies(self, dagbag):
        """Test task dependencies are correctly set."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        # Get tasks
        extract_task = dag.get_task('extract_and_validate_data')
        load_task = dag.get_task('load_raw_data_to_postgres')
        calculate_task = dag.get_task('calculate_standard_deviations')
        save_task = dag.get_task('save_results_to_postgres')
        cleanup_task = dag.get_task('cleanup_temp_files')
        
        # Check dependencies
        assert extract_task.downstream_task_ids == {'load_raw_data_to_postgres'}
        assert load_task.downstream_task_ids == {'calculate_standard_deviations'}
        assert calculate_task.downstream_task_ids == {'save_results_to_postgres'}
        assert save_task.downstream_task_ids == {'cleanup_temp_files'}
        assert cleanup_task.downstream_task_ids == set()
    
    def test_dag_tags(self, dagbag):
        """Test DAG has appropriate tags."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        expected_tags = {'finance', 'standard-deviation', 'etl'}
        actual_tags = set(dag.tags) if dag.tags else set()
        
        assert expected_tags.issubset(actual_tags), \
            f"Expected tags {expected_tags} not found in {actual_tags}"
    
    def test_dag_catchup_disabled(self, dagbag):
        """Test that DAG catchup is disabled."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        assert dag.catchup is False, "DAG catchup should be disabled"
    
    def test_dag_max_active_runs(self, dagbag):
        """Test DAG max active runs setting."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        assert dag.max_active_runs == 1, \
            f"Expected max_active_runs=1, got {dag.max_active_runs}"
    
    def test_task_timeouts(self, dagbag):
        """Test that tasks have reasonable timeouts."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        for task_id, task in dag.task_dict.items():
            # Check that tasks have execution timeout (if applicable)
            if hasattr(task, 'execution_timeout'):
                if task.execution_timeout is not None:
                    assert task.execution_timeout <= timedelta(hours=2), \
                        f"Task {task_id} timeout too long: {task.execution_timeout}"
    
    def test_task_retries(self, dagbag):
        """Test task retry configuration."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        for task_id, task in dag.task_dict.items():
            # Tasks should have reasonable retry configuration
            assert task.retries >= 0, f"Task {task_id} has negative retries"
            assert task.retries <= 3, f"Task {task_id} has too many retries: {task.retries}"
            
            if task.retry_delay:
                assert task.retry_delay <= timedelta(minutes=10), \
                    f"Task {task_id} retry delay too long: {task.retry_delay}"
    
    def test_python_operator_tasks(self, dagbag):
        """Test Python operator tasks have valid callables."""
        dag = dagbag.get_dag('stdev_calculation_pipeline')
        
        python_tasks = [
            'extract_and_validate_data',
            'calculate_standard_deviations',
            'cleanup_temp_files'
        ]
        
        for task_id in python_tasks:
            task = dag.get_task(task_id)
            assert hasattr(task, 'python_callable'), \
                f"Task {task_id} should have python_callable"
            assert callable(task.python_callable), \
                f"Task {task_id} python_callable is not callable"
