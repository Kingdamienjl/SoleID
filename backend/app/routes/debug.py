"""
Debug/logging endpoints for receiving remote device logs.
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

router = APIRouter()

# Directory to store received logs
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "device_logs")
os.makedirs(LOGS_DIR, exist_ok=True)


class LogEntry(BaseModel):
    timestamp: int
    tag: str
    level: str
    message: str
    data: Dict[str, Any] = {}


class LogUploadRequest(BaseModel):
    device_id: str
    device_model: str
    device_manufacturer: str
    android_version: str
    sdk_int: int
    app_version: str
    app_version_code: int
    log_file: str
    entries: List[Dict[str, Any]]
    uploaded_at: int


class LogUploadResponse(BaseModel):
    success: bool
    entries_received: int
    device_id: str


class DeviceInfo(BaseModel):
    device_id: str
    device_model: str
    device_manufacturer: str
    android_version: str
    sdk_int: int
    app_version: str
    app_version_code: int
    last_seen: str
    log_count: int


class DeviceListResponse(BaseModel):
    devices: List[DeviceInfo]
    total: int


@router.post("/debug/logs", response_model=LogUploadResponse)
async def upload_device_logs(request: LogUploadRequest) -> LogUploadResponse:
    """
    Receive debug logs from a remote device.
    Logs are stored in device_logs/{device_id}/{date}.ndjson
    """
    try:
        # Create device-specific directory
        device_dir = os.path.join(LOGS_DIR, request.device_id)
        os.makedirs(device_dir, exist_ok=True)

        # Write device info
        info_file = os.path.join(device_dir, "device_info.json")
        device_info = {
            "device_id": request.device_id,
            "device_model": request.device_model,
            "device_manufacturer": request.device_manufacturer,
            "android_version": request.android_version,
            "sdk_int": request.sdk_int,
            "app_version": request.app_version,
            "app_version_code": request.app_version_code,
            "last_seen": datetime.utcnow().isoformat(),
        }
        with open(info_file, "w") as f:
            json.dump(device_info, f, indent=2)

        # Extract date from log file name (format: YYYY-MM-DD.ndjson)
        log_date = request.log_file.replace(".ndjson", "")
        log_file = os.path.join(device_dir, f"{log_date}.ndjson")

        # Append entries to log file
        with open(log_file, "a") as f:
            for entry in request.entries:
                # Add server receipt time
                entry["_received_at"] = request.uploaded_at
                entry["_server_time"] = datetime.utcnow().isoformat()
                f.write(json.dumps(entry) + "\n")

        print(f"Received {len(request.entries)} logs from device {request.device_id}")

        return LogUploadResponse(
            success=True,
            entries_received=len(request.entries),
            device_id=request.device_id,
        )

    except Exception as e:
        print(f"Log upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/devices", response_model=DeviceListResponse)
async def list_devices() -> DeviceListResponse:
    """
    List all devices that have uploaded logs.
    """
    devices = []

    if not os.path.exists(LOGS_DIR):
        return DeviceListResponse(devices=[], total=0)

    for device_id in os.listdir(LOGS_DIR):
        device_dir = os.path.join(LOGS_DIR, device_id)
        if not os.path.isdir(device_dir):
            continue

        info_file = os.path.join(device_dir, "device_info.json")
        if os.path.exists(info_file):
            with open(info_file) as f:
                info = json.load(f)

            # Count log entries
            log_count = 0
            for log_file in os.listdir(device_dir):
                if log_file.endswith(".ndjson"):
                    with open(os.path.join(device_dir, log_file)) as f:
                        log_count += sum(1 for _ in f)

            devices.append(DeviceInfo(
                device_id=info.get("device_id", device_id),
                device_model=info.get("device_model", "Unknown"),
                device_manufacturer=info.get("device_manufacturer", "Unknown"),
                android_version=info.get("android_version", "Unknown"),
                sdk_int=info.get("sdk_int", 0),
                app_version=info.get("app_version", "Unknown"),
                app_version_code=info.get("app_version_code", 0),
                last_seen=info.get("last_seen", "Unknown"),
                log_count=log_count,
            ))

    # Sort by last_seen descending
    devices.sort(key=lambda d: d.last_seen, reverse=True)

    return DeviceListResponse(devices=devices, total=len(devices))


@router.get("/debug/logs/{device_id}")
async def get_device_logs(
    device_id: str,
    date: Optional[str] = None,
    limit: int = 100,
    level: Optional[str] = None,
    tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get logs for a specific device.

    - **device_id**: Device ID
    - **date**: Optional date filter (YYYY-MM-DD)
    - **limit**: Maximum entries to return
    - **level**: Filter by log level (INFO, WARN, ERROR, DEBUG)
    - **tag**: Filter by log tag
    """
    device_dir = os.path.join(LOGS_DIR, device_id)
    if not os.path.exists(device_dir):
        raise HTTPException(status_code=404, detail="Device not found")

    entries = []

    # Get log files (sorted by date descending)
    log_files = sorted(
        [f for f in os.listdir(device_dir) if f.endswith(".ndjson")],
        reverse=True
    )

    if date:
        log_files = [f for f in log_files if f.startswith(date)]

    for log_file in log_files:
        if len(entries) >= limit:
            break

        with open(os.path.join(device_dir, log_file)) as f:
            for line in f:
                if len(entries) >= limit:
                    break

                try:
                    entry = json.loads(line)

                    # Apply filters
                    if level and entry.get("level") != level:
                        continue
                    if tag and entry.get("tag") != tag:
                        continue

                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

    # Sort by timestamp descending
    entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)

    return {
        "device_id": device_id,
        "entries": entries[:limit],
        "total": len(entries),
    }


@router.delete("/debug/logs/{device_id}")
async def delete_device_logs(device_id: str) -> Dict[str, str]:
    """
    Delete all logs for a device.
    """
    device_dir = os.path.join(LOGS_DIR, device_id)
    if not os.path.exists(device_dir):
        raise HTTPException(status_code=404, detail="Device not found")

    import shutil
    shutil.rmtree(device_dir)

    return {"message": f"Logs for device {device_id} deleted"}
