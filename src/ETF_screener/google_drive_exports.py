"""Helpers for optional Google Drive / Google Sheets exports."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
GOOGLE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
DEFAULT_AUTO_EXPORT_FOLDER_NAME = "Auto Exports"


class GoogleDriveExportError(RuntimeError):
    """Raised when a Drive export cannot be completed."""


def _slugify(value: object, fallback: str = "na") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip().lower()).strip(
        "-"
    )
    return cleaned or fallback


def _disqualifier_suffix(disqualifiers: dict[str, bool] | None) -> str:
    normalized = disqualifiers or {}
    parts: list[str] = []
    if normalized.get("exclude_overbought"):
        parts.append("xob")
    if normalized.get("exclude_weak_liquidity"):
        parts.append("xliq")
    if normalized.get("exclude_unprofitable"):
        parts.append("xnp")
    return "-".join(parts) if parts else "base"


def build_screen_google_sheet_title(
    *,
    strategy_name: str = "",
    scan_scope: str = "",
    exchange: str = "",
    ticker_list: str = "",
    disqualifiers: dict[str, bool] | None = None,
    exported_at: datetime | None = None,
) -> str:
    """Build a stable, settings-aware export title for a screen run."""
    exported_at = exported_at or datetime.now()
    timestamp = exported_at.strftime("%y%m%dT%H%M")
    scope = _slugify(scan_scope or exchange or "xetra", fallback="xetra")
    strategy = _slugify(strategy_name or "top-matches", fallback="top-matches")
    disq = _disqualifier_suffix(disqualifiers)
    list_marker = ""
    if scope in {"list", "all-lists"} and str(ticker_list or "").strip():
        list_marker = "-custom-list"
    title = f"screen-{scope}-{strategy}{list_marker}-{disq}-{timestamp}"
    return title[:100]


def _sheet_rows_from_frame(frame: pd.DataFrame) -> list[list[Any]]:
    if frame is None or frame.empty:
        return []
    rows: list[list[Any]] = [list(frame.columns)]
    for row in frame.itertuples(index=False, name=None):
        cleaned_row: list[Any] = []
        for value in row:
            if isinstance(value, float):
                cleaned_row.append(None if pd.isna(value) else round(value, 6))
            elif pd.isna(value):
                cleaned_row.append("")
            else:
                cleaned_row.append(value)
        rows.append(cleaned_row)
    return rows


@dataclass
class GoogleSheetsDriveExporter:
    """Create native Google Sheets exports in a target Drive folder."""

    credentials_info: dict[str, Any]
    folder_id: str | None = None
    folder_name: str = DEFAULT_AUTO_EXPORT_FOLDER_NAME

    @classmethod
    def from_env(cls) -> "GoogleSheetsDriveExporter":
        raw_json = os.getenv("ETF_GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "").strip()
        json_path = os.getenv("ETF_GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "").strip()
        folder_id = os.getenv("ETF_GOOGLE_DRIVE_AUTO_EXPORT_FOLDER_ID", "").strip()
        folder_name = (
            os.getenv("ETF_GOOGLE_DRIVE_AUTO_EXPORT_FOLDER_NAME", "").strip()
            or DEFAULT_AUTO_EXPORT_FOLDER_NAME
        )

        credentials_info: dict[str, Any] | None = None
        if raw_json:
            try:
                credentials_info = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                raise GoogleDriveExportError(
                    "ETF_GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON is not valid JSON"
                ) from exc
        elif json_path:
            try:
                with open(json_path, "r", encoding="utf-8") as handle:
                    credentials_info = json.load(handle)
            except OSError as exc:
                raise GoogleDriveExportError(
                    f"Could not read service account file: {json_path}"
                ) from exc
            except json.JSONDecodeError as exc:
                raise GoogleDriveExportError(
                    f"Service account file is not valid JSON: {json_path}"
                ) from exc

        if not credentials_info:
            raise GoogleDriveExportError(
                "Set ETF_GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON or "
                "ETF_GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE to enable Google exports."
            )

        return cls(
            credentials_info=credentials_info,
            folder_id=folder_id or None,
            folder_name=folder_name,
        )

    def _build_clients(self):
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
        except ModuleNotFoundError as exc:
            raise GoogleDriveExportError(
                "Google export dependencies are missing. Install "
                "google-api-python-client and google-auth."
            ) from exc

        creds = Credentials.from_service_account_info(
            self.credentials_info,
            scopes=[GOOGLE_DRIVE_SCOPE, GOOGLE_SHEETS_SCOPE],
        )
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return drive, sheets

    def _resolve_folder_id(self, drive_service) -> str:
        if self.folder_id:
            return self.folder_id

        escaped_folder_name = self.folder_name.replace("'", "\\'")
        query = (
            "mimeType = 'application/vnd.google-apps.folder' "
            f"and name = '{escaped_folder_name}' "
            "and trashed = false"
        )
        result = (
            drive_service.files()
            .list(
                q=query,
                fields="files(id, name)",
                pageSize=10,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files = result.get("files") or []
        if not files:
            raise GoogleDriveExportError(
                f'Could not find a Google Drive folder named "{self.folder_name}".'
            )
        self.folder_id = str(files[0]["id"])
        return self.folder_id

    def export_frame(
        self,
        frame: pd.DataFrame,
        *,
        title: str,
        metadata_rows: list[list[Any]] | None = None,
    ) -> dict[str, Any]:
        if frame is None or frame.empty:
            raise GoogleDriveExportError("Cannot export an empty result set.")

        drive_service, sheets_service = self._build_clients()
        folder_id = self._resolve_folder_id(drive_service)
        metadata_rows = metadata_rows or []

        spreadsheet = (
            sheets_service.spreadsheets()
            .create(
                body={
                    "properties": {"title": title},
                    "sheets": [
                        {"properties": {"title": "Matches"}},
                        {"properties": {"title": "Meta"}},
                    ],
                },
                fields="spreadsheetId,spreadsheetUrl",
            )
            .execute()
        )
        spreadsheet_id = str(spreadsheet["spreadsheetId"])
        spreadsheet_url = str(spreadsheet["spreadsheetUrl"])

        updates = [
            {
                "range": "Matches!A1",
                "values": _sheet_rows_from_frame(frame),
            }
        ]
        if metadata_rows:
            updates.append({"range": "Meta!A1", "values": metadata_rows})

        (
            sheets_service.spreadsheets()
            .values()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"valueInputOption": "USER_ENTERED", "data": updates},
            )
            .execute()
        )

        (
            sheets_service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "updateSheetProperties": {
                                "properties": {
                                    "sheetId": 0,
                                    "gridProperties": {"frozenRowCount": 1},
                                },
                                "fields": "gridProperties.frozenRowCount",
                            }
                        },
                        {
                            "autoResizeDimensions": {
                                "dimensions": {
                                    "sheetId": 0,
                                    "dimension": "COLUMNS",
                                    "startIndex": 0,
                                    "endIndex": len(frame.columns),
                                }
                            }
                        },
                    ]
                },
            )
            .execute()
        )

        parent_meta = (
            drive_service.files()
            .get(
                fileId=spreadsheet_id,
                fields="parents",
                supportsAllDrives=True,
            )
            .execute()
        )
        existing_parents = ",".join(parent_meta.get("parents") or [])
        update_kwargs = {
            "fileId": spreadsheet_id,
            "addParents": folder_id,
            "supportsAllDrives": True,
            "fields": "id, parents",
        }
        if existing_parents:
            update_kwargs["removeParents"] = existing_parents
        drive_service.files().update(**update_kwargs).execute()

        return {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_url": spreadsheet_url,
            "folder_id": folder_id,
            "folder_name": self.folder_name,
            "title": title,
        }
