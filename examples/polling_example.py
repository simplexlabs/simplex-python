"""
Polling Example for Simplex Python SDK

This example demonstrates how to run a workflow and poll for its completion
using the Simplex SDK v2.0.
"""

import os
import time

from simplex import SimplexClient, SimplexError


def main() -> None:
    # Get API key from environment
    api_key = os.environ.get("SIMPLEX_API_KEY")
    if not api_key:
        print("Error: SIMPLEX_API_KEY environment variable is required")
        return

    # Get workflow ID from environment or use a default
    workflow_id = os.environ.get("WORKFLOW_ID")
    if not workflow_id:
        print("Error: WORKFLOW_ID environment variable is required")
        return

    # Initialize the client
    client = SimplexClient(api_key=api_key)

    try:
        # Run the workflow
        print(f"Starting workflow: {workflow_id}")
        response = client.run_workflow(
            workflow_id,
            variables={"key": "value"},  # Add your variables here
        )

        session_id = response["session_id"]
        print(f"Session started: {session_id}")
        print(f"VNC URL: {response['vnc_url']}")

        # Poll for completion
        print("\nPolling for completion...")
        while True:
            status = client.get_session_status(session_id)

            if not status["in_progress"]:
                break

            print("  Still running...")
            time.sleep(2)

        # Check result
        if status["success"]:
            print("\nWorkflow completed successfully!")
            print(f"Scraper outputs: {status['scraper_outputs']}")
            print(f"File metadata: {status['file_metadata']}")

            # Download files if any
            if status["file_metadata"]:
                print("\nDownloading files...")
                files = client.download_session_files(session_id)
                with open("session_files.zip", "wb") as f:
                    f.write(files)
                print("Files saved to session_files.zip")
        else:
            print("\nWorkflow failed!")
            print(f"Metadata: {status['metadata']}")

    except SimplexError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
