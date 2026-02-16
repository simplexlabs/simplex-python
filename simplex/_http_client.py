"""
Internal HTTP client for the Simplex SDK.

This module provides a robust HTTP client with automatic retry logic,
error handling, and support for various request types.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import requests

from simplex.errors import (
    AuthenticationError,
    NetworkError,
    RateLimitError,
    SimplexError,
    ValidationError,
)

__version__ = "3.0.2"


class HttpClient:
    """
    Internal HTTP client with retry logic and error handling.

    This client handles all communication with the Simplex API, including:
    - Automatic retry with exponential backoff for 429, 5xx errors
    - Error mapping to custom exceptions
    - Support for form-encoded and JSON requests
    - File downloads
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for the API (e.g., 'https://api.simplex.sh')
            api_key: Your Simplex API key
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Base delay between retries in seconds (default: 1.0)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": api_key,
                "User-Agent": f"Simplex-Python-SDK/{__version__}",
            }
        )

    def _should_retry(self, status_code: int | None) -> bool:
        """Determine if a request should be retried based on status code."""
        if status_code is None:
            return True  # Network error
        return status_code == 429 or status_code >= 500

    def _handle_error(self, response: requests.Response) -> SimplexError:
        """Convert HTTP errors to appropriate exception types."""
        status_code = response.status_code

        data = None
        try:
            data = response.json()
            if isinstance(data, dict):
                message = data.get("message") or data.get("error") or "An error occurred"
            else:
                message = str(data)
        except ValueError:
            message = response.text or "An error occurred"

        if status_code == 400:
            return ValidationError(message, data=data)
        elif status_code in [401, 403]:
            return AuthenticationError(message)
        elif status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
            return RateLimitError(message, retry_after=retry_after_seconds)
        else:
            return SimplexError(message, status_code=status_code, data=data)

    def _make_request(
        self,
        method: str,
        path: str,
        data: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            data: Request body data
            params: Query parameters
            headers: Additional headers for this request
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            SimplexError: If the request fails after all retries
        """
        url = f"{self.base_url}{path}"
        attempt = 0
        last_exception: SimplexError | None = None

        while attempt <= self.max_retries:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    data=data,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )

                if not response.ok:
                    error = self._handle_error(response)

                    if self._should_retry(response.status_code) and attempt < self.max_retries:
                        attempt += 1
                        time.sleep(self.retry_delay * attempt)
                        continue

                    raise error

                return response

            except requests.exceptions.RequestException as e:
                last_exception = NetworkError(str(e))

                if attempt < self.max_retries:
                    attempt += 1
                    time.sleep(self.retry_delay * attempt)
                    continue

                raise last_exception

        if last_exception:
            raise last_exception
        raise NetworkError("Request failed after all retries")

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request and return JSON response."""
        response = self._make_request("GET", path, params=params)
        return response.json()

    def post(
        self,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> Any:
        """
        Make a POST request with form-encoded data.

        Args:
            path: API endpoint path
            data: Form data to send

        Returns:
            Parsed JSON response
        """
        import json as json_module

        form_data = {}
        if data:
            for key, value in data.items():
                if value is not None:
                    if isinstance(value, (dict, list)):
                        form_data[key] = json_module.dumps(value)
                    else:
                        form_data[key] = str(value)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = self._make_request(
            "POST",
            path,
            data=urlencode(form_data) if form_data else None,
            headers=headers,
        )
        return response.json()

    def post_json(self, path: str, data: dict | None = None) -> Any:
        """POST with JSON body."""
        response = self._make_request("POST", path, json=data)
        return response.json()

    def patch_json(self, path: str, data: dict | None = None) -> Any:
        """PATCH with JSON body."""
        response = self._make_request("PATCH", path, json=data)
        return response.json()

    def stream_sse(self, url: str) -> Any:
        """Connect to an SSE endpoint and yield parsed events.

        Uses absolute URL (not base_url) since SSE endpoints are on container tunnels.
        The generator ends cleanly when the connection closes (e.g. session finished).
        """
        import json as json_module

        response = self.session.get(url, stream=True, timeout=None)
        response.raise_for_status()
        try:
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    try:
                        yield json_module.loads(line[6:])
                    except json_module.JSONDecodeError:
                        continue
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
            return  # Connection closed — session ended

    def post_to_url(self, url: str, json_data: dict) -> Any:
        """POST JSON to an absolute URL (not relative to base_url)."""
        response = self.session.post(url, json=json_data, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_from_url(self, url: str, params: dict | None = None) -> Any:
        """GET from an absolute URL (not relative to base_url)."""
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def download_file(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        """
        Download a file from the API.

        Args:
            path: API endpoint path
            params: Query parameters

        Returns:
            File content as bytes
        """
        response = self._make_request("GET", path, params=params)
        return response.content
