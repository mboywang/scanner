"""
Appends scanned-document records to the finance team's Excel log
(`Scanned Documents Log.xlsx`, sheet "Document Log").

If the workbook is open in Excel (Windows file lock), rows are queued to a
local pending file and flushed automatically on the next successful write, so
nothing is ever lost.
"""
import os
import json
import tempfile
from datetime import datetime

import openpyxl

from scanner_log import get_logger, activity

SHEET_NAME = "Document Log"
COLUMNS = [
    "Date Processed", "Original Filename", "Filed Filename", "Addressed To",
    "Sender Name", "Letter Date", "Due Date", "Amount Due", "Description",
    "Tasks", "Filed Location", "ClickUp Task URL", "Entity", "Subfolder",
]


class ExcelLogger:
    def __init__(self, xlsx_path):
        self.xlsx_path = xlsx_path
        self.log = get_logger()
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        self.pending_path = os.path.join(base, "ScannerApp", "pending_rows.jsonl")
        os.makedirs(os.path.dirname(self.pending_path), exist_ok=True)

    # ---- public API -----------------------------------------------------
    def append_scan(self, pdf_path, fields, filed_location="", subfolder=""):
        """Build a row from extracted fields and add it to the log (or queue it).

        filed_location/subfolder let a backfill record where a scan already lives;
        live scans leave them blank (the file stays in the main folder).
        """
        row = self._row_from_fields(pdf_path, fields or {})
        if filed_location:
            row["Filed Location"] = filed_location
        if subfolder:
            row["Subfolder"] = subfolder
        self._append_rows([row])

    def flush_pending(self):
        """Try to write any previously-queued rows. Returns count flushed."""
        queued = self._read_pending()
        if not queued:
            return 0
        try:
            self._write_rows(queued)
        except PermissionError:
            return 0  # still locked; leave the queue in place
        self._clear_pending()
        activity(self.log, f"Excel: flushed {len(queued)} queued row(s) into the log")
        return len(queued)

    # ---- row building ---------------------------------------------------
    def _row_from_fields(self, pdf_path, f):
        return {
            "Date Processed": datetime.now().strftime("%m/%d/%Y"),
            "Original Filename": os.path.basename(pdf_path),
            "Filed Filename": "",             # finance fills after filing
            "Addressed To": f.get("addressed_to", ""),
            "Sender Name": f.get("sender_name", ""),
            "Letter Date": f.get("letter_date", ""),
            "Due Date": f.get("due_date", ""),
            "Amount Due": f.get("amount_due", ""),
            "Description": f.get("description", ""),
            "Tasks": f.get("tasks", ""),
            "Filed Location": "",             # finance fills
            "ClickUp Task URL": "",           # finance fills
            "Entity": f.get("entity", ""),
            "Subfolder": f.get("subfolder", ""),
        }

    # ---- writing --------------------------------------------------------
    def _append_rows(self, rows):
        # Always try to drain the queue first so order is roughly preserved.
        all_rows = self._read_pending() + rows
        try:
            self._write_rows(all_rows)
            self._clear_pending()
            for r in rows:
                activity(self.log,
                         f"Excel: logged '{r['Original Filename']}' "
                         f"(sender='{r['Sender Name']}', amount='{r['Amount Due']}')")
        except PermissionError:
            # Workbook is open in Excel - queue for later instead of losing data.
            self._queue(rows)
            activity(self.log,
                     f"Excel locked (open in Excel?) - queued {len(rows)} row(s) "
                     f"to add automatically later")

    def _write_rows(self, rows):
        """Open the workbook, append rows to the Document Log sheet, save."""
        if os.path.exists(self.xlsx_path):
            wb = openpyxl.load_workbook(self.xlsx_path)
            ws = wb[SHEET_NAME] if SHEET_NAME in wb.sheetnames else wb.active
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = SHEET_NAME
            ws.append(COLUMNS)

        # Map each expected column to its position from the header row.
        header = [c.value for c in ws[1]]
        col_index = {name: i for i, name in enumerate(header) if name in COLUMNS}

        for row in rows:
            values = [""] * len(header)
            for name, idx in col_index.items():
                values[idx] = row.get(name, "")
            ws.append(values)

        wb.save(self.xlsx_path)

    # ---- pending queue --------------------------------------------------
    def _queue(self, rows):
        with open(self.pending_path, "a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    def _read_pending(self):
        if not os.path.exists(self.pending_path):
            return []
        rows = []
        with open(self.pending_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
        return rows

    def _clear_pending(self):
        try:
            if os.path.exists(self.pending_path):
                os.remove(self.pending_path)
        except Exception:
            pass
