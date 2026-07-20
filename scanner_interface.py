import os
import subprocess
import tempfile
import glob
from datetime import datetime
from PIL import Image
import shutil
from scanner_log import get_logger, activity

class ScannerInterface:
    def __init__(self):
        self.output_folder = r"C:\Users\mboyw\MSPbots.ai\Back Office Team - Home scanner"
        self.log = get_logger()
        # Persistent working area. Scanned pages are written here and only
        # deleted AFTER a PDF is successfully saved, so an interrupted scan
        # (app closed, crash, orphaned subprocess) can always be recovered.
        base = os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()
        self.work_folder = os.path.join(base, 'ScannerApp', 'pending')
        # Path of the most recently saved scan PDF (for the OCR/Excel pipeline).
        self.last_saved_pdf = None
        self.ensure_output_folder()
        os.makedirs(self.work_folder, exist_ok=True)

    def ensure_output_folder(self):
        """Create output folder if it doesn't exist"""
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder, exist_ok=True)

    def generate_filename(self):
        """Generate a date-based filename"""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        return f"Scan_{timestamp}.pdf"

    def _unique_output_path(self):
        """Return an output path that does not clobber an existing file."""
        filename = self.generate_filename()
        output_path = os.path.join(self.output_folder, filename)
        counter = 1
        stem = filename[:-4]  # strip ".pdf"
        while os.path.exists(output_path):
            output_path = os.path.join(self.output_folder, f"{stem}_{counter}.pdf")
            counter += 1
        return output_path

    def _pages_to_pdf(self, batch_dir, callback=None):
        """
        Convert every scanned page (page_*.bmp) in batch_dir into a single PDF
        saved to the output folder. Returns the output path, or None if there
        were no usable pages. This is the salvage path: it builds a PDF from
        whatever actually made it to disk, regardless of how the scan ended.
        """
        page_files = sorted(glob.glob(os.path.join(batch_dir, "page_*.bmp")))
        if not page_files:
            return None

        if callback:
            callback(f"Converting {len(page_files)} pages to PDF...")

        images = []
        for page_file in page_files:
            try:
                img = Image.open(page_file)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Force load into memory so the PDF save doesn't depend on the
                # underlying file still existing / being readable.
                img.load()
                images.append(img)
            except Exception:
                # Skip an unreadable page but keep the rest of the scan.
                continue

        if not images:
            return None

        output_path = self._unique_output_path()
        if len(images) == 1:
            images[0].save(output_path, 'PDF')
        else:
            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:],
                format='PDF'
            )

        for img in images:
            try:
                img.close()
            except Exception:
                pass

        return output_path

    def recover_pending(self, callback=None):
        """
        Convert any leftover scanned pages from a previous interrupted session
        into PDFs so no scan is ever lost. Called at startup. Returns the number
        of scans recovered.
        """
        recovered = 0
        for batch_dir in glob.glob(os.path.join(self.work_folder, "batch_*")):
            if not os.path.isdir(batch_dir):
                continue
            try:
                output_path = self._pages_to_pdf(batch_dir, callback=callback)
                if output_path:
                    recovered += 1
                    activity(self.log, f"RECOVERED interrupted scan -> {os.path.basename(output_path)}")
                    if callback:
                        callback(f"Recovered: {os.path.basename(output_path)}")
                else:
                    self.log.debug("Discarded empty leftover batch: %s", batch_dir)
                # Whether or not it had pages, the batch is now handled.
                shutil.rmtree(batch_dir, ignore_errors=True)
            except Exception:
                # Leave the batch in place so it can be retried next launch.
                self.log.exception("Recovery failed for batch %s", batch_dir)
                continue
        return recovered

    def scan_document(self, callback=None):
        """
        Automatic multi-page scan - scans all pages until feeder is empty and
        saves them as a single PDF.

        Pages are written to a persistent batch folder and converted to PDF from
        whatever reached disk, so a partial/interrupted scan is never wasted.
        """
        # Persistent per-scan batch folder (survives crashes / early exit).
        batch_dir = os.path.join(
            self.work_folder,
            "batch_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        )
        os.makedirs(batch_dir, exist_ok=True)
        vbs_script = os.path.join(batch_dir, "multi_scan.vbs")

        try:
            self.log.info("Scan started (batch %s)", os.path.basename(batch_dir))
            if callback:
                callback("Scanning all pages...")

            # VBScript that scans multiple pages by calling Transfer() repeatedly
            vbs_content = f'''Set objDeviceManager = CreateObject("WIA.DeviceManager")

On Error Resume Next

If objDeviceManager.DeviceInfos.Count > 0 Then
    Set objDevice = objDeviceManager.DeviceInfos(1).Connect()

    If Err.Number <> 0 Then
        Wscript.Echo "ERROR_CONNECT"
        Wscript.Quit 1
    End If

    Set objItem = objDevice.Items(1)

    Dim pageCount
    pageCount = 0

    Dim i
    For i = 1 To 999
        Err.Clear

        ' Each Transfer() call gets next page from feeder
        Set objImage = objItem.Transfer()

        If Err.Number <> 0 Then
            ' Feeder empty - we're done
            If pageCount > 0 Then
                Wscript.Echo "DONE:" & pageCount
                Wscript.Quit 0
            Else
                Wscript.Echo "ERROR_NO_PAGES"
                Wscript.Quit 1
            End If
        End If

        pageCount = pageCount + 1
        Dim filePath
        filePath = "{batch_dir}\\page_" & Right("00000" & pageCount, 5) & ".bmp"
        objImage.SaveFile(filePath)

        If Err.Number <> 0 Then
            Wscript.Echo "ERROR_SAVE"
            Wscript.Quit 1
        End If

        Wscript.Echo "PAGE:" & pageCount
    Next

Else
    Wscript.Echo "ERROR_NO_SCANNER"
    Wscript.Quit 1
End If
'''

            with open(vbs_script, 'w', encoding='utf-8') as f:
                f.write(vbs_content)

            # Run the VBScript
            result = subprocess.run(
                ['cscript.exe', vbs_script],
                capture_output=True,
                text=True,
                timeout=300
            )
            output = (result.stdout or "").strip()

            # Report per-page progress
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('PAGE:') and callback:
                    callback(f"Scanned page {line.split(':')[1]}...")

            # SALVAGE: build the PDF from whatever pages reached disk, even if
            # the script reported a partial error (e.g. ERROR_SAVE mid-batch).
            page_count = len(glob.glob(os.path.join(batch_dir, "page_*.bmp")))
            output_path = self._pages_to_pdf(batch_dir, callback=callback)
            if output_path:
                self.last_saved_pdf = output_path
                activity(self.log, f"SCAN saved {page_count} page(s) -> {os.path.basename(output_path)}")
                if callback:
                    callback(f"Saved: {os.path.basename(output_path)}")
                shutil.rmtree(batch_dir, ignore_errors=True)
                return True

            # No pages were produced - surface a useful reason.
            if 'ERROR_NO_SCANNER' in output:
                reason = "No scanner found - check connection"
            elif 'ERROR_CONNECT' in output:
                reason = "Could not connect to scanner"
            elif 'ERROR_NO_PAGES' in output:
                reason = "No pages scanned - check feeder"
            else:
                reason = "Scan failed - no pages captured"
            activity(self.log, f"SCAN FAILED - {reason}")
            if callback:
                callback(reason)
            shutil.rmtree(batch_dir, ignore_errors=True)
            return False

        except subprocess.TimeoutExpired:
            # Even on timeout, salvage whatever was scanned before giving up.
            output_path = self._pages_to_pdf(batch_dir, callback=callback)
            if output_path:
                self.last_saved_pdf = output_path
                activity(self.log, f"SCAN salvaged after timeout -> {os.path.basename(output_path)}")
                if callback:
                    callback(f"Saved (after timeout): {os.path.basename(output_path)}")
                shutil.rmtree(batch_dir, ignore_errors=True)
                return True
            activity(self.log, "SCAN FAILED - timeout, no pages captured")
            if callback:
                callback("Scan timeout")
            # Keep the batch dir on failure so recover_pending can retry it.
            return False

        except Exception as e:
            # On unexpected errors, try to salvage; keep the batch for recovery
            # if salvage isn't possible.
            self.log.exception("Unexpected scan error")
            output_path = self._pages_to_pdf(batch_dir, callback=callback)
            if output_path:
                self.last_saved_pdf = output_path
                activity(self.log, f"SCAN salvaged after error -> {os.path.basename(output_path)}")
                if callback:
                    callback(f"Saved (after error): {os.path.basename(output_path)}")
                shutil.rmtree(batch_dir, ignore_errors=True)
                return True
            activity(self.log, f"SCAN FAILED - error: {e}")
            if callback:
                callback(f"Error: {str(e)}")
            return False

    def cleanup(self):
        """Remove any empty leftover batch folders (safe, non-destructive)."""
        try:
            for batch_dir in glob.glob(os.path.join(self.work_folder, "batch_*")):
                if os.path.isdir(batch_dir) and not glob.glob(os.path.join(batch_dir, "page_*.bmp")):
                    shutil.rmtree(batch_dir, ignore_errors=True)
        except Exception:
            pass
