"""Private stdin entrypoint for a supervised calculation in any hosting runtime."""

import json
import sys


def main():
    payload = json.load(sys.stdin.buffer)
    sys.path[:] = payload["python_path"]

    from lottolab.worker import perform_job

    perform_job(payload["job_id"], payload["settings"])


if __name__ == "__main__":
    main()
