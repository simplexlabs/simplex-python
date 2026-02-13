"""
Editor Session Example — Simplex Python SDK

Creates a workflow on example.com, starts an interactive editor session,
sends a message to click the "More information..." link, and streams
live events from the browser agent.

Requires SIMPLEX_API_KEY environment variable to be set.
"""

import os

from simplex import SimplexClient, SimplexError


def main() -> None:
    client = SimplexClient(
        api_key=os.environ["SIMPLEX_API_KEY"],
        timeout=120,  # Editor sessions take 10-15s to start
    )

    try:
        # 1. Start an editor session on example.com
        print("Starting editor session on https://example.com ...")
        result = client.start_editor_session(
            name="Example.com Demo",
            url="https://example.com",
        )

        session_id = result["session_id"]
        print(f"Session:     {session_id}")
        print(f"Workflow:    {result['workflow_id']}")
        print(f"VNC:         {result['vnc_url']}")
        print()

        # 2. Send a message to the agent
        print('Sending message: "Click the More information... link"')
        client.send_message(
            result["message_url"],
            'Click the "More information..." link on the page.',
        )

        # 3. Stream live events from the session
        print("\nStreaming events (Ctrl+C to stop):\n")
        for event in client.stream_session(result["logs_url"]):
            event_type = event.get("event") or event.get("type", "")

            if event_type == "RunContent":
                print(event.get("content", ""), end="")
            elif event_type == "ToolCallStarted":
                tool_name = event.get("tool_name", "unknown")
                print(f"\n--- Tool: {tool_name} ---")
            elif event_type == "ToolCallCompleted":
                print("--- done ---\n")
            elif event_type in ("RunCompleted", "RunFinished"):
                print("\nSession completed.")
                break
            elif event_type == "RunError":
                print(f"\nError: {event.get('error', '')}")
                break

        # 4. Clean up
        client.close_session(session_id)
        print("Session closed.")

    except KeyboardInterrupt:
        print("\nInterrupted. Closing session...")
        client.close_session(result["session_id"])
    except SimplexError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
