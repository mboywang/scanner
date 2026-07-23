import os
import queue
import tkinter as tk
from tkinter import messagebox, ttk
import threading
from scanner_interface import ScannerInterface
from scanner_log import get_logger, activity
from excel_logger import ExcelLogger

EXCEL_LOG_NAME = "Scanned Documents Log.xlsx"


class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner Application")
        self.root.geometry("450x580")
        self.root.resizable(False, False)

        self.log = get_logger()
        activity(self.log, "===== Scanner app started =====")
        self.scanner = ScannerInterface()
        self.is_scanning = False

        # OCR + Excel logging pipeline. Scans are OCR'd on a background worker
        # so the app stays usable while a document is being read.
        self.xlsx = ExcelLogger(os.path.join(self.scanner.output_folder, EXCEL_LOG_NAME))
        self.ocr = None  # QwenOCR, created lazily on first use (heavy model)
        self.ocr_queue = queue.Queue()

        self.setup_ui()

        threading.Thread(target=self._ocr_worker, daemon=True).start()

        # Recover any scans left over from a previous interrupted session so
        # scanned pages are never lost, even if the app was closed mid-scan.
        threading.Thread(target=self._startup_recovery, daemon=True).start()

        # Periodically merge any rows queued while Excel was locked, so they
        # land shortly after the workbook is closed (no need to scan again).
        self.root.after(30000, self._periodic_flush)

    def _periodic_flush(self):
        """Try to merge queued rows into the Excel log, then reschedule."""
        def work():
            try:
                merged = self.xlsx.flush_pending()
                if merged:
                    self.set_ocr_status(
                        f"Merged {merged} pending row(s) into the Excel log", success=True)
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()
        self.root.after(30000, self._periodic_flush)

    def _startup_recovery(self):
        """Convert leftover pages from an interrupted session into PDFs, and
        flush any Excel rows queued while the workbook was previously locked."""
        try:
            recovered = self.scanner.recover_pending(callback=self.update_status)
            # Any recovered scans still need OCR + logging.
            if recovered > 0 and self.scanner.last_saved_pdf:
                self.ocr_queue.put(self.scanner.last_saved_pdf)
            flushed = self.xlsx.flush_pending()
            if recovered > 0:
                self.root.after(0, lambda: self.update_status(
                    f"Recovered {recovered} interrupted scan(s)!", success=True))
            elif flushed > 0:
                self.root.after(0, lambda: self.set_ocr_status(
                    f"Added {flushed} queued row(s) to the Excel log", success=True))
            else:
                self.root.after(0, lambda: self.update_status("Ready", success=True))
        except Exception:
            pass

    def _ensure_ocr(self):
        """Create the Qwen OCR engine on first use; return None if unavailable."""
        if self.ocr is None:
            try:
                from qwen_ocr import QwenOCR
                self.ocr = QwenOCR(callback=self.set_ocr_status)
            except Exception as e:
                self.log.warning("OCR unavailable: %s", e)
                return None
        return self.ocr

    def _ocr_worker(self):
        """Background worker: OCR each scanned PDF and append it to the Excel log."""
        while True:
            pdf_path = self.ocr_queue.get()
            name = os.path.basename(pdf_path)
            try:
                ocr = self._ensure_ocr()
                if ocr is None:
                    self.root.after(0, lambda: self.set_ocr_status(
                        "OCR engine unavailable - scan saved but not logged", success=False))
                    continue
                self.root.after(0, lambda n=name: self.set_ocr_status(f"Reading {n} (OCR)..."))
                fields = ocr.extract_fields(pdf_path, callback=self.set_ocr_status)
                self.xlsx.append_scan(pdf_path, fields)
                self.root.after(0, lambda n=name: self.set_ocr_status(
                    f"Logged {n} to Excel", success=True))
            except Exception as e:
                self.log.exception("OCR/log failed for %s", name)
                self.root.after(0, lambda e=e: self.set_ocr_status(
                    f"OCR/log error: {e}", success=False))
            finally:
                self.ocr_queue.task_done()

    def setup_ui(self):
        """Create the UI elements"""
        # Title
        title = ttk.Label(
            self.root,
            text="Epson ES-500W II Scanner",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=15)

        # Info frame
        info_frame = ttk.LabelFrame(self.root, text="Scan Settings", padding=10)
        info_frame.pack(pady=10, padx=15, fill=tk.BOTH)

        settings_text = (
            "• Resolution: 300 DPI  • Color: Color\n"
            "• Format: PDF  • Pages: All until empty"
        )
        ttk.Label(info_frame, text=settings_text, justify=tk.LEFT).pack(anchor=tk.W)

        ttk.Label(
            info_frame,
            text=f"Folder: {self.scanner.output_folder}",
            font=("Arial", 8),
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))

        # Status label
        self.status_label = ttk.Label(
            self.root,
            text="Ready",
            font=("Arial", 10),
            foreground="green"
        )
        self.status_label.pack(pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(
            self.root,
            mode='indeterminate',
            length=300
        )
        self.progress.pack(pady=5)

        # OCR / Excel-logging status (runs in the background after a scan)
        self.ocr_status_label = ttk.Label(
            self.root,
            text="",
            font=("Arial", 9),
            foreground="gray",
            wraplength=400,
            justify=tk.CENTER
        )
        self.ocr_status_label.pack(pady=(0, 5))

        # Button frame
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=15)

        # Scan button
        self.scan_button = ttk.Button(
            button_frame,
            text="SCAN",
            command=self.start_scan
        )
        self.scan_button.grid(row=0, column=0, padx=5, ipadx=20, ipady=10)

        # Utilities frame
        util_frame = ttk.Frame(self.root)
        util_frame.pack(pady=10)

        ttk.Button(
            util_frame,
            text="Open Folder",
            command=self.open_output_folder
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            util_frame,
            text="Exit",
            command=self.root.quit
        ).pack(side=tk.LEFT, padx=5)

    def start_scan(self):
        """Start scanning in a separate thread"""
        if self.is_scanning:
            return

        self.is_scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="Scanning...", foreground="blue")

        scan_thread = threading.Thread(target=self.perform_scan)
        scan_thread.daemon = True
        scan_thread.start()

    def perform_scan(self):
        """Execute the scan operation. Scanned PDFs are saved to the output
        folder; files are never auto-moved into category subfolders."""
        try:
            success = self.scanner.scan_document(callback=self.update_status)

            if success:
                self.root.after(0, lambda: self.update_status("Scan completed!", success=True))
                # Hand the saved PDF to the background OCR/logging worker.
                pdf_path = self.scanner.last_saved_pdf
                if pdf_path:
                    self.root.after(0, lambda: self.set_ocr_status(
                        "Queued for OCR + Excel logging..."))
                    self.ocr_queue.put(pdf_path)
            else:
                self.root.after(0, lambda: self.update_status("Scan failed", success=False))

        except Exception as e:
            self.root.after(0, lambda: self.update_status(f"Error: {str(e)}", success=False))
        finally:
            self.is_scanning = False
            self.root.after(0, self.reset_ui)

    def update_status(self, message, success=None):
        """Update status label with message"""
        self.status_label.config(text=message)
        if success is True:
            self.status_label.config(foreground="green")
        elif success is False:
            self.status_label.config(foreground="red")
        else:
            self.status_label.config(foreground="blue")
        self.root.update()

    def set_ocr_status(self, message, success=None):
        """Update the OCR/logging status line (safe to call from any thread)."""
        def apply():
            self.ocr_status_label.config(text=message)
            if success is True:
                self.ocr_status_label.config(foreground="green")
            elif success is False:
                self.ocr_status_label.config(foreground="red")
            else:
                self.ocr_status_label.config(foreground="gray")
        # Marshal to the main thread; the background worker calls this too.
        try:
            self.root.after(0, apply)
        except RuntimeError:
            pass

    def reset_ui(self):
        """Reset UI after operation"""
        self.progress.stop()
        self.scan_button.config(state=tk.NORMAL)

    def open_output_folder(self):
        """Open the output folder in Windows Explorer"""
        import subprocess
        import os
        if os.path.exists(self.scanner.output_folder):
            subprocess.Popen(f'explorer "{self.scanner.output_folder}"')


def main():
    root = tk.Tk()
    app = ScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
