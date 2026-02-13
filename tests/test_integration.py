"""
Integration tests for the Simplex SDK.

These tests make real API calls and require valid credentials.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from simplex import SimplexClient, SimplexError, WorkflowError


def test_client_connection():
    """Test basic client connection with API key."""
    print("Testing client connection...")
    
    api_key = os.getenv('SIMPLEX_API_KEY')
    if not api_key:
        print("  ⚠ Skipped: SIMPLEX_API_KEY not set")
        return None
    
    try:
        client = SimplexClient(api_key=api_key)
        print("  ✓ Client created successfully")
        return True
    except Exception as e:
        print(f"  ✗ Failed to create client: {e}")
        return False


def test_create_workflow_session():
    """Test creating a workflow session."""
    print("\nTesting workflow session creation...")
    
    api_key = os.getenv('SIMPLEX_API_KEY')
    if not api_key:
        print("  ⚠ Skipped: SIMPLEX_API_KEY not set")
        return None
    
    try:
        client = SimplexClient(api_key=api_key)
        
        # Create a session
        session = client.create_workflow_session(
            name='test-session',
            url='https://example.com'
        )
        
        print(f"  ✓ Session created: {session.session_id}")
        print(f"    - Workflow ID: {session.workflow_id}")
        print(f"    - Livestream URL: {session.livestream_url}")
        
        # Close the session
        session.close()
        print("  ✓ Session closed successfully")
        
        return True
    except SimplexError as e:
        print(f"  ✗ API Error: {e.message}")
        if e.status_code:
            print(f"    Status Code: {e.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_run_workflow():
    """Test running a workflow."""
    print("\nTesting workflow execution...")
    
    api_key = os.getenv('SIMPLEX_API_KEY')
    workflow_id = os.getenv('WORKFLOW_ID')
    
    if not api_key:
        print("  ⚠ Skipped: SIMPLEX_API_KEY not set")
        return None
    
    if not workflow_id:
        print("  ⚠ Skipped: WORKFLOW_ID not set (optional test)")
        return None
    
    try:
        client = SimplexClient(api_key=api_key)
        
        # Run the workflow
        result = client.workflows.run(
            workflow_id,
            variables={'test': 'value'}
        )
        
        print(f"  ✓ Workflow started: {result['session_id']}")
        print(f"    - Success: {result['succeeded']}")
        print(f"    - Message: {result.get('message', 'N/A')}")
        
        # Check status
        status = client.workflows.get_status(result['session_id'])
        print(f"  ✓ Status retrieved: Completed={status['completed']}")
        
        return True
    except WorkflowError as e:
        print(f"  ✗ Workflow Error: {e.message}")
        if e.workflow_id:
            print(f"    Workflow ID: {e.workflow_id}")
        if e.session_id:
            print(f"    Session ID: {e.session_id}")
        return False
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_context_manager():
    """Test using WorkflowSession as context manager with agentic action."""
    print("\nTesting context manager usage with agentic action...")
    
    api_key = os.getenv('SIMPLEX_API_KEY')
    if not api_key:
        print("  ⚠ Skipped: SIMPLEX_API_KEY not set")
        return None
    
    try:
        client = SimplexClient(api_key=api_key)
        
        # Use context manager
        with client.create_workflow_session('test-cm', 'https://example.com') as session:
            print(f"  ✓ Session created in context: {session.session_id}")
            assert not session.is_closed, "Session should not be closed yet"
            
            # Execute agentic task
            result = session.agentic('return completed')
            print(f"  ✓ Agentic task executed: {result.get('succeeded', False)}")
            if result.get('result'):
                print(f"    - Result: {result['result']}")
        
        # Session should be closed after exiting context
        print("  ✓ Context manager exited successfully")
        assert session.is_closed, "Session should be closed after context exit"
        print("  ✓ Session automatically closed")
        
        return True
    except SimplexError as e:
        print(f"  ✗ API Error: {e.message}")
        return False
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def run_integration_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Simplex SDK Integration Tests")
    print("=" * 60)
    print("\nNote: These tests require valid API credentials")
    print("Set SIMPLEX_API_KEY environment variable to run tests")
    print("Optionally set WORKFLOW_ID to test workflow execution")
    print("=" * 60)
    
    tests = [
        test_client_connection,
        test_create_workflow_session,
        test_context_manager,
        test_run_workflow,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            result = test()
            if result is True:
                passed += 1
            elif result is False:
                failed += 1
            else:  # None means skipped
                skipped += 1
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)
    
    if skipped > 0:
        print("\nTo run skipped tests, set the required environment variables:")
        print("  export SIMPLEX_API_KEY='your-api-key'")
        print("  export WORKFLOW_ID='your-workflow-id'  # optional")
    
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)