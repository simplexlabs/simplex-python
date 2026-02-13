"""
Pause & Resume Example for Simplex Python SDK v3.0

Runs a workflow, pauses the session, resumes it, and polls to completion.
Requires SIMPLEX_API_KEY environment variable to be set.
"""

import os
import time

from simplex import SimplexClient, SimplexError

WORKFLOW_ID = "ec6dcf56-29ba-40b2-bd83-83e2b70631d6"


def main() -> None:
    client = SimplexClient(api_key=os.environ["SIMPLEX_API_KEY"])

    try:
        # 1. Run the workflow
        print(f"Starting workflow: {WORKFLOW_ID}")
        response = client.run_workflow(WORKFLOW_ID)
        session_id = response["session_id"]
        print(f"Session started: {session_id}")
        print(f"VNC URL: {response['vnc_url']}")

        # 2. Wait a bit, then pause
        time.sleep(5)
        print("\nPausing session...")
        pause_result = client.pause(session_id)
        print(f"Paused — key: {pause_result.get('pause_key')}")

        # 3. Resume the session
        print("Resuming session...")
        resume_result = client.resume(session_id)
        print(f"Resumed — type: {resume_result.get('pause_type')}")

        # 4. Poll for completion
        print("\nPolling for completion...")
        while True:
            status = client.get_session_status(session_id)
            if not status["in_progress"]:
                break
            print("  Still running...")
            time.sleep(2)

        # 5. Print result
        if status["success"]:
            print("\nWorkflow completed successfully!")
            print(f"Scraper outputs: {status['scraper_outputs']}")
        else:
            print("\nWorkflow failed.")

    except SimplexError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
