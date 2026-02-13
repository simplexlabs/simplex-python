# Test 06: Workflow CRUD via SDK

## Setup

```python
from simplex import SimplexClient

client = SimplexClient(
    api_key="YOUR_KEY",
    base_url="https://simplex-dev--api-server-and-container-service-fastapi-app.modal.run",
)
```

## Test 6A: Create workflow with all fields

```python
result = client.create_workflow(
    name="Full Workflow",
    url="https://example.com/start",
    actions=[],
    variables={"email": "", "password": ""},
    structured_output={"title": "string", "price": "number"},
    metadata="test-metadata-123",
)
print(result)
workflow_id = result["workflow"]["id"]
print(f"Created: {workflow_id}")
```

**Expected:** Workflow created with all fields.

## Test 6B: Create workflow with minimal fields

```python
result = client.create_workflow(name="Minimal Workflow")
print(result)
workflow_id = result["workflow"]["id"]
```

**Expected:** Workflow created with just a name, other fields null/empty.

## Test 6C: Get workflow

```python
result = client.get_workflow(workflow_id)
print(result)
assert result["workflow"]["name"] == "Minimal Workflow"
```

**Expected:** Returns the full workflow object.

## Test 6D: Update workflow fields

```python
result = client.update_workflow(
    workflow_id,
    name="Updated Name",
    url="https://example.com/updated",
)
print(result)
```

**Expected:** Returns updated workflow.

## Test 6E: Get workflow after update

```python
result = client.get_workflow(workflow_id)
assert result["workflow"]["name"] == "Updated Name"
assert result["workflow"]["url"] == "https://example.com/updated"
```

**Expected:** Changes persisted.

## Test 6F: Search for created workflows

```python
results = client.search_workflows(workflow_name="Updated Name")
print(results)
assert results["succeeded"]
found = [w for w in results["workflows"] if w.get("workflow_id") == workflow_id]
assert len(found) > 0
```

**Expected:** Finds the workflow by name.

## Test 6G: Get non-existent workflow

```python
from simplex import WorkflowError

try:
    client.get_workflow("00000000-0000-0000-0000-000000000000")
    assert False, "Should have raised"
except WorkflowError as e:
    print(f"Expected error: {e}")
```

**Expected:** Raises WorkflowError with 404.
