"""
Main SimplexClient class for the Simplex SDK.

This module provides the SimplexClient, which is the primary entry point
for interacting with the Simplex API.
"""

from __future__ import annotations

import json
from typing import Any

from simplex._http_client import HttpClient
from simplex.errors import WorkflowError
from simplex.types import (
    PauseSessionResponse,
    ResumeSessionResponse,
    RunWorkflowResponse,
    SearchWorkflowsResponse,
    SessionStatusResponse,
    StartEditorSessionResponse,
    UpdateWorkflowMetadataResponse,
)


class SimplexClient:
    """
    Main client for interacting with the Simplex API.

    This is the primary entry point for the SDK. It provides a flat API
    for all Simplex API functionality.

    Example:
        >>> from simplex import SimplexClient
        >>> client = SimplexClient(api_key="your-api-key")
        >>>
        >>> # Run a workflow
        >>> result = client.run_workflow("workflow-id", variables={"key": "value"})
        >>>
        >>> # Poll for completion
        >>> import time
        >>> while True:
        ...     status = client.get_session_status(result["session_id"])
        ...     if not status["in_progress"]:
        ...         break
        ...     time.sleep(1)
        >>>
        >>> if status["success"]:
        ...     print("Scraper outputs:", status["scraper_outputs"])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.simplex.sh",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the Simplex client.

        Args:
            api_key: Your Simplex API key (required)
            base_url: Base URL for the API (default: "https://api.simplex.sh")
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 1.0)

        Raises:
            ValueError: If api_key is not provided
        """
        if not api_key:
            raise ValueError("api_key is required")

        self._http_client = HttpClient(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

    def run_workflow(
        self,
        workflow_id: str,
        variables: dict[str, Any] | None = None,
        metadata: str | None = None,
        webhook_url: str | None = None,
    ) -> RunWorkflowResponse:
        """
        Run a workflow by its ID.

        Args:
            workflow_id: The ID of the workflow to run
            variables: Dictionary of variables to pass to the workflow
            metadata: Optional metadata string to attach to the workflow run
            webhook_url: Optional webhook URL for status updates

        Returns:
            RunWorkflowResponse with session_id and other details

        Raises:
            WorkflowError: If the workflow fails to start

        Example:
            >>> result = client.run_workflow(
            ...     "workflow-id",
            ...     variables={"email": "user@example.com"}
            ... )
            >>> print(f"Session ID: {result['session_id']}")
        """
        request_data: dict[str, Any] = {"workflow_id": workflow_id}

        if variables is not None:
            request_data["variables"] = variables
        if metadata is not None:
            request_data["metadata"] = metadata
        if webhook_url is not None:
            request_data["webhook_url"] = webhook_url

        try:
            response: RunWorkflowResponse = self._http_client.post(
                "/run_workflow",
                data=request_data,
            )
            return response
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(f"Failed to run workflow: {e}", workflow_id=workflow_id)

    def get_session_status(self, session_id: str) -> SessionStatusResponse:
        """
        Get the status of a session.

        Use this method to poll for workflow completion. The session is complete
        when `in_progress` is False.

        Args:
            session_id: The session ID to check

        Returns:
            SessionStatusResponse with status, metadata, and scraper outputs

        Raises:
            WorkflowError: If retrieving status fails

        Example:
            >>> status = client.get_session_status("session-123")
            >>> if not status["in_progress"]:
            ...     if status["success"]:
            ...         print("Success! Outputs:", status["scraper_outputs"])
            ...     else:
            ...         print("Failed")
        """
        try:
            response: SessionStatusResponse = self._http_client.get(
                f"/session/{session_id}/status"
            )
            return response
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(
                f"Failed to get session status: {e}",
                session_id=session_id,
            )

    def download_session_files(
        self,
        session_id: str,
        filename: str | None = None,
    ) -> bytes:
        """
        Download files from a session.

        Downloads files that were created or downloaded during a workflow session.
        If no filename is specified, all files are downloaded as a zip archive.

        Args:
            session_id: ID of the session to download files from
            filename: Optional specific filename to download

        Returns:
            File content as bytes

        Raises:
            WorkflowError: If file download fails

        Example:
            >>> # Download all files as zip
            >>> zip_data = client.download_session_files("session-123")
            >>> with open("files.zip", "wb") as f:
            ...     f.write(zip_data)
            >>>
            >>> # Download specific file
            >>> pdf_data = client.download_session_files("session-123", "report.pdf")
        """
        try:
            params: dict[str, str] = {"session_id": session_id}
            if filename:
                params["filename"] = filename

            content = self._http_client.download_file("/download_session_files", params=params)

            # Check if the response is a JSON error
            try:
                text = content.decode("utf-8")
                data = json.loads(text)
                if isinstance(data, dict) and data.get("succeeded") is False:
                    raise WorkflowError(
                        data.get("error") or "Failed to download session files",
                        session_id=session_id,
                    )
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Binary data (the file), which is what we want
                pass

            return content
        except WorkflowError:
            raise
        except Exception as e:
            raise WorkflowError(
                f"Failed to download session files: {e}",
                session_id=session_id,
            )

    def retrieve_session_replay(self, session_id: str) -> bytes:
        """
        Retrieve the session replay video for a completed session.

        Downloads a video (MP4) recording of the browser session after it
        has completed.

        Args:
            session_id: ID of the session to retrieve replay for

        Returns:
            Video content as bytes (MP4 format)

        Raises:
            WorkflowError: If retrieving session replay fails

        Example:
            >>> video_data = client.retrieve_session_replay("session-123")
            >>> with open("replay.mp4", "wb") as f:
            ...     f.write(video_data)
        """
        try:
            content = self._http_client.download_file(f"/retrieve_session_replay/{session_id}")
            return content
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(
                f"Failed to retrieve session replay: {e}",
                session_id=session_id,
            )

    def retrieve_session_logs(self, session_id: str) -> Any | None:
        """
        Retrieve the session logs for a session.

        Returns None if the session is still running or shutting down.
        Logs are only available for completed sessions.

        Args:
            session_id: ID of the session to retrieve logs for

        Returns:
            Parsed JSON logs containing session events and details,
            or None if the session is still running

        Raises:
            WorkflowError: If retrieving session logs fails

        Example:
            >>> logs = client.retrieve_session_logs("session-123")
            >>> if logs is None:
            ...     print("Session is still running, logs not yet available")
            ... else:
            ...     print(f"Got {len(logs)} log entries")
        """
        try:
            content = self._http_client.download_file(f"/retrieve_session_logs/{session_id}")
            text = content.decode("utf-8")
            response = json.loads(text)
            return response.get("logs")
        except json.JSONDecodeError as e:
            raise WorkflowError(
                f"Failed to parse session logs: {e}",
                session_id=session_id,
            )
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(
                f"Failed to retrieve session logs: {e}",
                session_id=session_id,
            )

    def pause(self, session_id: str) -> PauseSessionResponse:
        """
        Pause a running session.

        Args:
            session_id: The session ID to pause

        Returns:
            PauseSessionResponse with pause details

        Raises:
            WorkflowError: If pausing the session fails

        Example:
            >>> result = client.pause("session-123")
            >>> print(f"Paused with key: {result['pause_key']}")
        """
        try:
            response: PauseSessionResponse = self._http_client.post(
                "/pause",
                data={"session_id": session_id},
            )
            if not response.get("succeeded"):
                raise WorkflowError(
                    response.get("error", "Failed to pause session"),
                    session_id=session_id,
                )
            return response
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(
                f"Failed to pause session: {e}",
                session_id=session_id,
            )

    def resume(self, session_id: str) -> ResumeSessionResponse:
        """
        Resume a paused session.

        Args:
            session_id: The session ID to resume

        Returns:
            ResumeSessionResponse with resume details

        Raises:
            WorkflowError: If resuming the session fails

        Example:
            >>> result = client.resume("session-123")
            >>> print(f"Resumed, pause type: {result['pause_type']}")
        """
        try:
            response: ResumeSessionResponse = self._http_client.post(
                "/resume_session",
                data={"session_id": session_id},
            )
            if not response.get("succeeded"):
                raise WorkflowError(
                    response.get("error", "Failed to resume session"),
                    session_id=session_id,
                )
            return response
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(
                f"Failed to resume session: {e}",
                session_id=session_id,
            )

    def search_workflows(
        self,
        workflow_name: str | None = None,
        metadata: str | None = None,
    ) -> SearchWorkflowsResponse:
        """
        Search workflows by name and/or metadata.

        At least one of workflow_name or metadata must be provided.

        Args:
            workflow_name: Name of the workflow to search for
            metadata: Metadata string to search for

        Returns:
            SearchWorkflowsResponse with matching workflows

        Raises:
            ValueError: If neither workflow_name nor metadata is provided
            WorkflowError: If the search fails

        Example:
            >>> results = client.search_workflows(workflow_name="my-workflow")
            >>> for wf in results["workflows"]:
            ...     print(f"{wf['workflow_name']} ({wf['workflow_id']})")
        """
        if workflow_name is None and metadata is None:
            raise ValueError("At least one of workflow_name or metadata must be provided")

        params: dict[str, str] = {}
        if workflow_name is not None:
            params["workflow_name"] = workflow_name
        if metadata is not None:
            params["metadata"] = metadata

        try:
            response: SearchWorkflowsResponse = self._http_client.get(
                "/search_workflows",
                params=params,
            )
            return response
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(f"Failed to search workflows: {e}")

    def update_workflow_metadata(
        self,
        workflow_id: str,
        metadata: str,
    ) -> UpdateWorkflowMetadataResponse:
        """
        Update the metadata of a workflow.

        Args:
            workflow_id: The ID of the workflow to update
            metadata: The new metadata string

        Returns:
            UpdateWorkflowMetadataResponse with update confirmation

        Raises:
            WorkflowError: If updating the metadata fails

        Example:
            >>> result = client.update_workflow_metadata(
            ...     "workflow-123",
            ...     "new-metadata-value"
            ... )
            >>> print(f"Updated: {result['message']}")
        """
        try:
            response: UpdateWorkflowMetadataResponse = self._http_client.post(
                "/update_workflow_metadata",
                data={"workflow_id": workflow_id, "metadata": metadata},
            )
            if not response.get("succeeded"):
                raise WorkflowError(
                    "Failed to update workflow metadata",
                    workflow_id=workflow_id,
                )
            return response
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(
                f"Failed to update workflow metadata: {e}",
                workflow_id=workflow_id,
            )

    def get_workflow(self, workflow_id: str) -> Any:
        """
        Get a workflow by its ID.

        Args:
            workflow_id: The ID of the workflow to retrieve

        Returns:
            The full workflow object
        """
        try:
            return self._http_client.get(f"/workflow/{workflow_id}")
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(f"Failed to get workflow: {e}", workflow_id=workflow_id)

    def create_workflow(
        self,
        name: str,
        url: str | None = None,
        actions: list[Any] | None = None,
        variables: dict[str, Any] | None = None,
        structured_output: dict[str, Any] | None = None,
        metadata: str | None = None,
    ) -> Any:
        """
        Create a new workflow.

        Args:
            name: Name for the workflow
            url: Starting URL for the workflow
            actions: List of workflow actions
            variables: Workflow variables
            structured_output: Structured output definition
            metadata: Optional metadata string

        Returns:
            The created workflow object
        """
        data: dict[str, Any] = {"name": name}
        if url is not None:
            data["url"] = url
        if actions is not None:
            data["actions"] = actions
        if variables is not None:
            data["variables"] = variables
        if structured_output is not None:
            data["structured_output"] = structured_output
        if metadata is not None:
            data["metadata"] = metadata

        try:
            return self._http_client.post_json("/workflow", data=data)
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(f"Failed to create workflow: {e}")

    def update_workflow(self, workflow_id: str, **fields: Any) -> Any:
        """
        Update a workflow.

        Args:
            workflow_id: The ID of the workflow to update
            **fields: Fields to update (name, url, actions, variables, etc.)

        Returns:
            The updated workflow object
        """
        try:
            return self._http_client.patch_json(f"/workflow/{workflow_id}", data=fields)
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(f"Failed to update workflow: {e}", workflow_id=workflow_id)

    def start_editor_session(
        self,
        name: str,
        url: str,
        test_data: dict[str, Any] | None = None,
    ) -> StartEditorSessionResponse:
        """
        Start an editor session. Creates a workflow and starts a browser session.

        Args:
            name: Name for the workflow
            url: Starting URL
            test_data: Optional test data variables

        Returns:
            StartEditorSessionResponse with session_id, workflow_id, and URLs
        """
        data: dict[str, Any] = {"name": name, "url": url}
        if test_data is not None:
            data["test_data"] = test_data

        try:
            response: StartEditorSessionResponse = self._http_client.post_json(
                "/start_editor_session", data=data
            )
            if not response.get("succeeded"):
                raise WorkflowError("Failed to start editor session")
            return response
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(f"Failed to start editor session: {e}")

    def stream_session(self, logs_url: str) -> Any:
        """
        Stream SSE events from a live session.

        Args:
            logs_url: The logs_url (SSE endpoint) for the session

        Yields:
            Parsed event dicts from the SSE stream
        """
        return self._http_client.stream_sse(logs_url)

    def send_message(self, message_url: str, message: str) -> Any:
        """
        Send a message to a live session.

        Args:
            message_url: The message_url for the session
            message: The message text to send

        Returns:
            Response from the message endpoint
        """
        return self._http_client.post_to_url(message_url, json_data={"message": message})

    def get_workflow_active_session(self, workflow_id: str) -> dict:
        """
        Get the active session for a workflow.

        Returns session_id, logs_url, message_url, vnc_url for the most
        recent session associated with the given workflow.

        Args:
            workflow_id: The workflow ID to look up

        Returns:
            Dict with session_id, status, logs_url, message_url, vnc_url
        """
        return self._http_client.get(f"/workflow/{workflow_id}/active_session")

    def close_session(self, session_id: str) -> Any:
        """
        Close a workflow session.

        Args:
            session_id: The session ID to close

        Returns:
            Response from the close endpoint
        """
        try:
            return self._http_client.post(
                "/close_workflow_session",
                data={"session_id": session_id},
            )
        except Exception as e:
            if isinstance(e, WorkflowError):
                raise
            raise WorkflowError(f"Failed to close session: {e}", session_id=session_id)
