from __future__ import annotations

import json
import os
from typing import List, Dict, Any

# Minimal placeholder abstraction; real implementation would auth with Google Drive


class DriveService:
    def __init__(self) -> None:
        # If DRIVE_SERVICE_ACCOUNT_JSON is unset, operate in no-op/mock mode
        self.service_account_json = os.getenv("DRIVE_SERVICE_ACCOUNT_JSON")

    def list_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        return []

    def download(self, file_id: str) -> bytes:
        return b""

    def upload(self, file_path: str, parent_id: str) -> str:
        # Return a mock file id
        return f"mock_{os.path.basename(file_path)}"


_drive_singleton: DriveService | None = None


def get_drive_service() -> DriveService:
    global _drive_singleton
    if _drive_singleton is None:
        _drive_singleton = DriveService()
    return _drive_singleton
