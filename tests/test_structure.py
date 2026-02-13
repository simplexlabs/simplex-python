"""
Structure validation tests for the Simplex SDK.

These tests validate the SDK structure and imports without making API calls.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import simplex
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all main imports work."""
    print("Testing imports...")
    
    try:
        from simplex import SimplexClient
        print("  ✓ SimplexClient imported")
    except ImportError as e:
        print(f"  ✗ Failed to import SimplexClient: {e}")
        return False
    
    try:
        from simplex import (
            SimplexError,
            NetworkError,
            ValidationError,
            AuthenticationError,
            RateLimitError,
            WorkflowError,
        )
        print("  ✓ All error classes imported")
    except ImportError as e:
        print(f"  ✗ Failed to import errors: {e}")
        return False
    
    try:
        from simplex.resources.workflow import Workflow
        from simplex.resources.workflow_session import WorkflowSession
        print("  ✓ Resource classes imported")
    except ImportError as e:
        print(f"  ✗ Failed to import resource classes: {e}")
        return False
    
    return True


def test_client_instantiation():
    """Test that SimplexClient can be instantiated."""
    print("\nTesting client instantiation...")
    
    try:
        from simplex import SimplexClient
        
        # Test with required api_key
        client = SimplexClient(api_key="test-key")
        print("  ✓ Client created with api_key")
        
        # Test with custom options
        client = SimplexClient(
            api_key="test-key",
            timeout=60,
            max_retries=5,
            retry_delay=2
        )
        print("  ✓ Client created with custom options")
        
        # Verify workflows resource exists
        assert hasattr(client, 'workflows'), "Client missing workflows resource"
        print("  ✓ Client has workflows resource")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_error_hierarchy():
    """Test error class hierarchy."""
    print("\nTesting error hierarchy...")
    
    try:
        from simplex import (
            SimplexError,
            NetworkError,
            ValidationError,
            AuthenticationError,
            RateLimitError,
            WorkflowError,
        )
        
        # Test that all errors inherit from SimplexError
        assert issubclass(NetworkError, SimplexError)
        assert issubclass(ValidationError, SimplexError)
        assert issubclass(AuthenticationError, SimplexError)
        assert issubclass(RateLimitError, SimplexError)
        assert issubclass(WorkflowError, SimplexError)
        print("  ✓ All error classes inherit from SimplexError")
        
        # Test error instantiation
        error = SimplexError("test", status_code=500)
        assert error.message == "test"
        assert error.status_code == 500
        print("  ✓ Error instantiation works")
        
        # Test RateLimitError with retry_after
        rate_error = RateLimitError("Rate limited", retry_after=60)
        assert rate_error.retry_after == 60
        print("  ✓ RateLimitError has retry_after attribute")
        
        # Test WorkflowError with IDs
        workflow_error = WorkflowError("Failed", workflow_id="wf-123", session_id="sess-456")
        assert workflow_error.workflow_id == "wf-123"
        assert workflow_error.session_id == "sess-456"
        print("  ✓ WorkflowError has workflow_id and session_id attributes")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_workflow_session_context_manager():
    """Test that WorkflowSession supports context manager protocol."""
    print("\nTesting WorkflowSession context manager...")
    
    try:
        from simplex.resources.workflow_session import WorkflowSession
        from simplex.http_client import HttpClient
        
        # Create a mock session
        http_client = HttpClient("https://api.test.com", "test-key")
        session_data = {
            'sessionId': 'test-session',
            'workflowId': 'test-workflow',
            'livestreamUrl': 'https://test.com/live',
            'connectUrl': 'https://test.com/connect',
            'vncUrl': 'https://test.com/vnc'
        }
        
        session = WorkflowSession(http_client, session_data)
        
        # Verify properties
        assert session.session_id == 'test-session'
        assert session.workflow_id == 'test-workflow'
        assert session.livestream_url == 'https://test.com/live'
        print("  ✓ WorkflowSession properties set correctly")
        
        # Verify context manager methods exist
        assert hasattr(session, '__enter__')
        assert hasattr(session, '__exit__')
        print("  ✓ WorkflowSession has context manager methods")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_workflow_resource_methods():
    """Test that Workflow resource has all expected methods."""
    print("\nTesting Workflow resource methods...")
    
    try:
        from simplex import SimplexClient
        
        client = SimplexClient(api_key="test-key")
        workflow = client.workflows
        
        # Check for all expected methods
        expected_methods = [
            'run', 'get_status', 'create_workflow_session',
            'agentic', 'run_agent', 'start_segment', 'finish_segment',
            'start_capture', 'stop_capture', 'close_workflow_session'
        ]
        
        for method_name in expected_methods:
            assert hasattr(workflow, method_name), f"Missing method: {method_name}"
            assert callable(getattr(workflow, method_name)), f"{method_name} is not callable"
        
        print(f"  ✓ All {len(expected_methods)} expected methods exist")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_client_utility_methods():
    """Test SimplexClient utility methods."""
    print("\nTesting SimplexClient utility methods...")
    
    try:
        from simplex import SimplexClient
        
        client = SimplexClient(api_key="test-key")
        
        # Check for utility methods
        expected_methods = [
            'create_workflow_session', 'get_session_store',
            'download_session_files', 'add_2fa_config',
            'update_api_key', 'set_custom_header', 'remove_custom_header'
        ]
        
        for method_name in expected_methods:
            assert hasattr(client, method_name), f"Missing method: {method_name}"
            assert callable(getattr(client, method_name)), f"{method_name} is not callable"
        
        print(f"  ✓ All {len(expected_methods)} utility methods exist")
        
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def run_all_tests():
    """Run all structure validation tests."""
    print("=" * 60)
    print("Running Simplex SDK Structure Validation Tests")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_client_instantiation,
        test_error_hierarchy,
        test_workflow_session_context_manager,
        test_workflow_resource_methods,
        test_client_utility_methods,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)