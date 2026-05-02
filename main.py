import tkinter as tk
from tkinter import messagebox, ttk
import threading
from scanner_interface import ScannerInterface
from document_processor import DocumentProcessor


class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scanner Application")
        self.root.geometry("450x550")
        self.root.resizable(False, False)

        self.scanner = ScannerInterface()
        self.processor = DocumentProcessor(self.scanner.output_folder)
        self.is_scanning = False
        self.is_processing = False
        self.auto_process = tk.BooleanVar(value=True)

        self.setup_ui()

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

        # Auto-process checkbox
        ttk.Checkbutton(
            info_frame,
            text="Auto-categorize after scan",
            variable=self.auto_process
        ).pack(anchor=tk.W, pady=5)

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

        # Process button
        self.process_button = ttk.Button(
            button_frame,
            text="PROCESS FILES",
            command=self.start_process
        )
        self.process_button.grid(row=0, column=1, padx=5, ipadx=15, ipady=10)

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
        if self.is_scanning or self.is_processing:
            return

        self.is_scanning = True
        self.scan_button.config(state=tk.DISABLED)
        self.process_button.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="Scanning...", foreground="blue")

        scan_thread = threading.Thread(target=self.perform_scan)
        scan_thread.daemon = True
        scan_thread.start()

    def perform_scan(self):
        """Execute the scan operation"""
        try:
            success = self.scanner.scan_document(callback=self.update_status)

            if success:
                self.root.after(0, lambda: self.update_status("Scan completed!", success=True))

                # Auto-process if enabled
                if self.auto_process.get():
                    self.root.after(0, lambda: self.update_status("Auto-categorizing...", success=None))
                    self.root.after(500, self.auto_process_scans)
            else:
                self.root.after(0, lambda: self.update_status("Scan failed", success=False))

        except Exception as e:
            self.root.after(0, lambda: self.update_status(f"Error: {str(e)}", success=False))
        finally:
            self.is_scanning = False
            self.root.after(0, self.reset_ui)

    def start_process(self):
        """Start processing files in a separate thread"""
        if self.is_scanning or self.is_processing:
            return

        self.is_processing = True
        self.scan_button.config(state=tk.DISABLED)
        self.process_button.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="Processing files...", foreground="blue")

        process_thread = threading.Thread(target=self.perform_process)
        process_thread.daemon = True
        process_thread.start()

    def perform_process(self):
        """Execute the file processing operation"""
        try:
            # Get newly scanned files (in main folder)
            processed = self.processor.process_folder(
                self.scanner.output_folder,
                callback=self.update_status
            )

            if processed > 0:
                self.root.after(0, lambda: self.update_status(f"Categorized {processed} files!", success=True))
            else:
                self.root.after(0, lambda: self.update_status("No files to process", success=False))

        except Exception as e:
            self.root.after(0, lambda: self.update_status(f"Error: {str(e)}", success=False))
        finally:
            self.is_processing = False
            self.root.after(0, self.reset_ui)

    def auto_process_scans(self):
        """Auto-process newly scanned files"""
        try:
            self.processor.process_folder(
                self.scanner.output_folder,
                callback=self.update_status
            )
        except:
            pass

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

    def reset_ui(self):
        """Reset UI after operation"""
        self.progress.stop()
        self.scan_button.config(state=tk.NORMAL)
        self.process_button.config(state=tk.NORMAL)

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
