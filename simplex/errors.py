"""
Custom exception classes for the Simplex SDK.

This module defines a hierarchy of exceptions that can be raised by the SDK,
allowing for specific error handling based on the type of error encountered.
"""

from __future__ import annotations

from typing import Any


class SimplexError(Exception):
    """
    Base exception class for all Simplex SDK errors.

    All custom exceptions in the SDK inherit from this class, making it easy
    to catch any SDK-related error with a single except clause.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code if applicable
        data: Additional error data or context
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        data: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.data = data

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class NetworkError(SimplexError):
    """
    Raised when a network-related error occurs.

    This includes connection failures, timeouts, and other network issues
    that prevent communication with the Simplex API.
    """

    def __init__(self, message: str):
        super().__init__(f"Network error: {message}")


class ValidationError(SimplexError):
    """
    Raised when request validation fails (HTTP 400).

    This indicates that the request data was invalid or malformed,
    such as missing required fields or invalid parameter values.
    """

    def __init__(self, message: str, data: Any = None):
        super().__init__(message, status_code=400, data=data)


class AuthenticationError(SimplexError):
    """
    Raised when authentication fails (HTTP 401 or 403).

    This typically indicates an invalid API key or insufficient permissions
    to access the requested resource.
    """

    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class RateLimitError(SimplexError):
    """
    Raised when rate limit is exceeded (HTTP 429).

    The Simplex API has rate limits to prevent abuse. When exceeded,
    this error is raised with information about when to retry.

    Attributes:
        retry_after: Number of seconds to wait before retrying
    """

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class WorkflowError(SimplexError):
    """
    Raised when a workflow operation fails.

    This is a specialized error for workflow-related failures,
    including session creation, workflow execution, and agent tasks.

    Attributes:
        workflow_id: The ID of the workflow that failed (if applicable)
        session_id: The ID of the session that failed (if applicable)
    """

    def __init__(
        self,
        message: str,
        workflow_id: str | None = None,
        session_id: str | None = None,
    ):
        super().__init__(
            message,
            status_code=500,
            data={"workflow_id": workflow_id, "session_id": session_id},
        )
        self.workflow_id = workflow_id
        self.session_id = session_id
