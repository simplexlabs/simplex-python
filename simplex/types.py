"""
Type definitions for the Simplex SDK.

This module contains TypedDict classes used for type hinting throughout the SDK.
"""

from __future__ import annotations

from typing import Any, TypedDict


class FileMetadata(TypedDict):
    """
    Metadata for a file downloaded or created during a session.

    Attributes:
        filename: The filename
        download_url: The URL the file was downloaded from
        file_size: File size in bytes
        download_timestamp: ISO timestamp when the file was downloaded/created
    """

    filename: str
    download_url: str
    file_size: int
    download_timestamp: str


class SessionStatusResponse(TypedDict, total=False):
    """
    Response from polling session status.

    Attributes:
        in_progress: Whether the session is still running
        success: Whether the session completed successfully (None while in progress)
        metadata: Custom metadata provided when the session was started
        workflow_metadata: Metadata from the workflow definition
        file_metadata: Metadata for files downloaded during the session
        scraper_outputs: Scraper outputs collected during the session, keyed by output name
        structured_output: Structured output fields from workflow execution (None while in progress)
        final_message: A summary of what the agent accomplished (None while in progress)
        paused: Whether the session is currently paused
        paused_key: The pause key if the session is paused
    """

    in_progress: bool
    success: bool | None
    metadata: dict[str, Any]
    workflow_metadata: dict[str, Any]
    file_metadata: list[FileMetadata]
    scraper_outputs: dict[str, Any]
    structured_output: dict[str, Any] | None
    final_message: str | None
    paused: bool
    paused_key: str


class RunWorkflowResponse(TypedDict):
    """
    Response from running a workflow.

    Attributes:
        succeeded: Whether the workflow started successfully
        message: Human-readable status message
        session_id: Unique identifier for this workflow session
        vnc_url: URL for VNC access to the workflow session
        logs_url: URL for viewing session logs
    """

    succeeded: bool
    message: str
    session_id: str
    vnc_url: str
    logs_url: str


class PauseSessionResponse(TypedDict, total=False):
    """
    Response from pausing a session.

    Attributes:
        succeeded: Whether the pause operation succeeded
        action: The action that was performed
        pause_key: The key associated with the pause
        error: Error message if the operation failed
    """

    succeeded: bool
    action: str
    pause_key: str
    error: str


class ResumeSessionResponse(TypedDict, total=False):
    """
    Response from resuming a paused session.

    Attributes:
        succeeded: Whether the resume operation succeeded
        action: The action that was performed
        pause_type: The type of pause ('external' or 'internal')
        key: The key associated with the pause
        error: Error message if the operation failed
    """

    succeeded: bool
    action: str
    pause_type: str
    key: str
    error: str


class SearchWorkflowItem(TypedDict, total=False):
    """
    A single workflow item returned from a search.

    Attributes:
        workflow_id: The workflow's unique identifier
        workflow_name: The workflow's name
        variables: Variables defined in the workflow
        metadata: Optional metadata string
    """

    workflow_id: str
    workflow_name: str
    variables: dict[str, Any]
    metadata: str


class SearchWorkflowsResponse(TypedDict):
    """
    Response from searching workflows.

    Attributes:
        succeeded: Whether the search succeeded
        workflows: List of matching workflows
        count: Total number of matching workflows
    """

    succeeded: bool
    workflows: list[SearchWorkflowItem]
    count: int


class UpdateWorkflowMetadataResponse(TypedDict):
    """
    Response from updating workflow metadata.

    Attributes:
        succeeded: Whether the update succeeded
        message: Human-readable status message
        workflow_id: The workflow that was updated
        metadata: The updated metadata string
    """

    succeeded: bool
    message: str
    workflow_id: str
    metadata: str


class StartEditorSessionResponse(TypedDict, total=False):
    """
    Response from starting an editor session.

    Attributes:
        succeeded: Whether the session started successfully
        workflow_id: The newly created workflow ID
        session_id: The session ID
        vnc_url: URL for VNC access
        logs_url: URL for the SSE log stream
        message_url: URL for posting messages to the session
        filesystem_url: URL for filesystem events
    """

    succeeded: bool
    workflow_id: str
    session_id: str
    vnc_url: str
    logs_url: str
    message_url: str | None
    filesystem_url: str | None


class WebhookPayload(TypedDict, total=False):
    """
    Payload received from a Simplex webhook.

    Attributes:
        success: Whether the session completed successfully
        agent_response: The agent's response text
        session_id: The session identifier
        file_metadata: Metadata for files created during the session
        scraper_outputs: Scraper outputs collected during the session
        session_metadata: Custom metadata attached to the session
        workflow_id: The workflow identifier
        workflow_metadata: Metadata from the workflow definition
        workflow_result: The workflow execution result
        structured_output: Structured output from the workflow
        screenshot_url: URL to a screenshot taken during the session
    """

    success: bool
    agent_response: str
    session_id: str
    file_metadata: list[FileMetadata]
    scraper_outputs: dict[str, Any]
    session_metadata: dict[str, Any]
    workflow_id: str
    workflow_metadata: dict[str, Any]
    workflow_result: dict[str, Any]
    structured_output: dict[str, Any]
    screenshot_url: str
