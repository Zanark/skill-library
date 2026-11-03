import argparse
import os
import sys
import threading
import webbrowser

import uvicorn


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "explorer":
        from .explorer import main as explorer_main
        raise SystemExit(explorer_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "workflow":
        from .workflow import main as workflow_main
        raise SystemExit(workflow_main(sys.argv[2:]))
    parser = argparse.ArgumentParser(description="ClipFarm local video clipping studio")
    parser.add_argument("--port", type=int, default=8741)
    parser.add_argument("--data-dir", help="Project database and output folder (default .clipfarm)")
    parser.add_argument("--open", action="store_true", help="Open the studio in your browser")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    if args.data_dir:
        os.environ["CLIPFARM_DATA_DIR"] = args.data_dir
    if args.open:
        timer = threading.Timer(1.5, webbrowser.open, args=(f"http://127.0.0.1:{args.port}",))
        timer.daemon = True
        timer.start()
    uvicorn.run("clipfarm.app:create_app", factory=True, host="127.0.0.1", port=args.port,
                timeout_graceful_shutdown=10)


if __name__ == "__main__":
    main()
