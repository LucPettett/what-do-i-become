"""Common filesystem paths for WDIB control plane."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = FRAMEWORK_DIR.parent
DEVICES_DIR = PROJECT_ROOT / "devices"
ENV_FILE = FRAMEWORK_DIR / ".env"
DEVICE_ID_FILE = FRAMEWORK_DIR / ".device_id"
MISSION_FILE = FRAMEWORK_DIR / "MISSION.md"

STATE_FILE_NAME = "state.json"
EVENTS_FILE_NAME = "events.ndjson"
RUNTIME_DIR_NAME = "runtime"
WORK_ORDERS_DIR_NAME = "work_orders"
WORKER_RESULTS_DIR_NAME = "worker_results"
HUMAN_MESSAGE_FILE_NAME = "human_message.txt"
SESSIONS_DIR_NAME = "sessions"
PUBLIC_DIR_NAME = "public"
PUBLIC_DAILY_DIR_NAME = "daily"
PUBLIC_STATUS_FILE_NAME = "status.json"
