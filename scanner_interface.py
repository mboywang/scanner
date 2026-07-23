import os
import subprocess
import tempfile
import glob
from datetime import datetime
from PIL import Image
import shutil
from scanner_log import get_logger, activity

# Scanned pages are written as page_0001.png, page_0002.png, ... by NAPS2.
# (Older builds used .bmp via WIA; match both so a leftover batch from a
# previous version can still be recovered.)
PAGE_GLOB = "page_*.png"
PAGE_GLOB_LEGACY = "page_*.bmp"

# NAPS2 (bundled/installed) is used to drive the scanner. Its console handles
# duplex ADF scanning reliably, unlike the legacy WIA Transfer() path which
# failed with out-of-memory errors on duplex for the Epson ES-500W II.
NAPS2_CONSOLE_CANDIDATES = [
    r"C:\Program Files\NAPS2\NAPS2.Console.exe",
    r"C:\Program Files (x86)\NAPS2\NAPS2.Console.exe",
]
# Inexact device-name match (NAPS2 accepts partial names). Specific enough to
# pick the Epson, tolerant of naming variants ("ES-500WII" / "ES-500W II").
SCANNER_DEVICE_MATCH = "ES-500"


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

    def _find_naps2(self):
        """Return the path to NAPS2.Console.exe, or None if not installed."""
        for path in NAPS2_CONSOLE_CANDIDATES:
            if os.path.exists(path):
                return path
        return None

    def _page_files(self, batch_dir):
        """All scanned page images in a batch, in scan order (png, then any
        legacy bmp), so PDF assembly and page counting share one source."""
        files = glob.glob(os.path.join(batch_dir, PAGE_GLOB))
        files += glob.glob(os.path.join(batch_dir, PAGE_GLOB_LEGACY))
        return sorted(files)

    def _is_blank_page(self, img):
        """
        Heuristic blank-page test, used to drop the empty back-sides that duplex
        scanning produces for single-sided documents.

        A page is "blank" when almost none of its pixels are dark enough to be
        ink. The test deliberately errs toward KEEPING a page when uncertain so
        that genuine (even sparse) content is never discarded.
        """
        try:
            gray = img.convert('L')
            # Ignore a thin border so feeder-edge shadows / black margins from
            # the ADF are not mistaken for content.
            w, h = gray.size
            mx, my = int(w * 0.04), int(h * 0.04)
            if w - 2 * mx > 20 and h - 2 * my > 20:
                gray = gray.crop((mx, my, w - mx, h - my))
            hist = gray.histogram()
            total = sum(hist) or 1
            # Pixels darker than ~190/255 count as ink (text / graphics); paper
            # white on this scanner sits well above that. Threshold picked from
            # measured 300-DPI pages: dust/noise ~0.03%, while the sparsest real
            # content (a short note or a signature) is ~0.17%. 0.1% sits safely
            # between, so noise is dropped but faint content is kept.
            ink = sum(hist[:190])
            return (ink / total) < 0.001
        except Exception:
            # If we can't tell, treat the page as non-blank so it is kept.
            return False

    def _pages_to_pdf(self, batch_dir, callback=None):
        """
        Convert every scanned page image in batch_dir into a single PDF saved
        to the output folder. Returns the output path, or None if there were no
        usable pages. This is the salvage path: it builds a PDF from
        whatever actually made it to disk, regardless of how the scan ended.
        """
        page_files = self._page_files(batch_dir)
        if not page_files:
            return None

        if callback:
            callback(f"Converting {len(page_files)} pages to PDF...")

        # Classify pages first so blank duplex back-sides can be dropped. We do
        # this in a separate pass so that if EVERY page looks blank we keep them
        # all rather than turning a scan into an empty PDF (never lose a scan).
        blank_flags = {}
        for page_file in page_files:
            try:
                with Image.open(page_file) as probe:
                    probe.load()
                    blank_flags[page_file] = self._is_blank_page(probe)
            except Exception:
                blank_flags[page_file] = False  # unreadable != blank
        drop_blanks = not all(blank_flags.get(p, False) for p in page_files)

        images = []
        skipped_blank = 0
        for page_file in page_files:
            if drop_blanks and blank_flags.get(page_file):
                skipped_blank += 1
                continue
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

        if skipped_blank:
            activity(self.log, f"Skipped {skipped_blank} blank page(s)")

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

        naps2 = self._find_naps2()
        if naps2 is None:
            activity(self.log, "SCAN FAILED - NAPS2 not installed")
            if callback:
                callback("Scanner software (NAPS2) not found")
            shutil.rmtree(batch_dir, ignore_errors=True)
            return False

        try:
            self.log.info("Scan started (batch %s)", os.path.basename(batch_dir))
            if callback:
                callback("Scanning all pages...")

            # Drive the scan through NAPS2's console. TWAIN + duplex reliably
            # captures BOTH sides of every sheet; the legacy WIA Transfer() path
            # failed with out-of-memory when duplex was requested on this Epson.
            # Each page is written as its own image (page_0001.png, ...) into the
            # persistent batch folder, so the existing salvage / blank-skip /
            # PDF-assembly pipeline is reused and a partial scan is never wasted.
            # Duplex is always on; blank back-sides of single-sided documents are
            # dropped later by _is_blank_page().
            cmd = [
                naps2,
                "-o", os.path.join(batch_dir, "page_$(nnnn).png"),
                "--driver", "twain",
                "--device", SCANNER_DEVICE_MATCH,
                "--source", "duplex",
                "--dpi", "300",
                "--bitdepth", "color",
                "--noprofile",
                "-f",  # overwrite (batch dir is fresh, but be explicit)
                "-v",  # verbose: emit per-page progress we relay to the UI
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
            self.log.debug("NAPS2 (exit %s) output:\n%s", result.returncode, output)

            # Relay NAPS2's per-page progress ("Scanned page N.") to the UI.
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('Scanned page') and callback:
                    callback(line.rstrip('.') + "...")

            # SALVAGE: build the PDF from whatever pages reached disk, even if
            # NAPS2 reported a partial error mid-batch.
            page_count = len(self._page_files(batch_dir))
            output_path = self._pages_to_pdf(batch_dir, callback=callback)
            if output_path:
                self.last_saved_pdf = output_path
                activity(self.log, f"SCAN saved {page_count} page(s) -> {os.path.basename(output_path)}")
                if callback:
                    callback(f"Saved: {os.path.basename(output_path)}")
                shutil.rmtree(batch_dir, ignore_errors=True)
                return True

            # No pages were produced - surface a useful reason from NAPS2's output.
            low = output.lower()
            if 'no devices' in low or 'no scanning device' in low or 'device not found' in low:
                reason = "No scanner found - check power/connection"
            elif 'no pages' in low or 'feeder' in low or 'empty' in low:
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
                if os.path.isdir(batch_dir) and not self._page_files(batch_dir):
                    shutil.rmtree(batch_dir, ignore_errors=True)
        except Exception:
            pass
