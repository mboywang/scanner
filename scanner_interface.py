import os
import subprocess
import tempfile
from datetime import datetime
from PIL import Image
import shutil

class ScannerInterface:
    def __init__(self):
        self.output_folder = r"C:\Users\mboyw\MSPbots.ai\Back Office Team - Home scanner"
        self.ensure_output_folder()
        self.temp_folder = tempfile.mkdtemp()

    def ensure_output_folder(self):
        """Create output folder if it doesn't exist"""
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder, exist_ok=True)

    def generate_filename(self):
        """Generate a date-based filename"""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        return f"Scan_{timestamp}.pdf"

    def scan_document(self, callback=None):
        """
        Automatic multi-page scan - scans all pages until feeder is empty
        Saves all pages as single PDF
        """
        try:
            if callback:
                callback("Scanning all pages...")

            vbs_script = os.path.join(self.temp_folder, "multi_scan.vbs")
            temp_dir = os.path.join(self.temp_folder, "pages")
            os.makedirs(temp_dir, exist_ok=True)

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
        filePath = "{temp_dir}\\page_" & Right("00000" & pageCount, 5) & ".bmp"
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

            # Parse output
            output = result.stdout.strip()
            page_count = 0
            success = False

            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('PAGE:'):
                    page_count = int(line.split(':')[1])
                    if callback:
                        callback(f"Scanned page {page_count}...")
                elif line.startswith('DONE:'):
                    page_count = int(line.split(':')[1])
                    success = True

            if not success:
                if 'ERROR_NO_PAGES' in output:
                    if callback:
                        callback("No pages scanned - check feeder")
                elif 'ERROR' in output:
                    if callback:
                        callback(f"Scan error")
                return False

            if success and page_count > 0:
                if callback:
                    callback(f"Converting {page_count} pages to PDF...")

                # Load all images and convert to PDF
                images = []
                for i in range(1, page_count + 1):
                    page_file = os.path.join(temp_dir, f"page_{i:05d}.bmp")
                    if os.path.exists(page_file):
                        img = Image.open(page_file)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        images.append(img)

                if images:
                    filename = self.generate_filename()
                    output_path = os.path.join(self.output_folder, filename)

                    # Save as multi-page PDF
                    if len(images) == 1:
                        images[0].save(output_path, 'PDF')
                    else:
                        images[0].save(
                            output_path,
                            save_all=True,
                            append_images=images[1:],
                            format='PDF'
                        )

                    if callback:
                        callback(f"Saved {page_count} pages!")

                    # Cleanup
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return True

            return False

        except subprocess.TimeoutExpired:
            if callback:
                callback("Scan timeout")
            return False
        except Exception as e:
            if callback:
                callback(f"Error: {str(e)}")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        try:
            shutil.rmtree(self.temp_folder, ignore_errors=True)
        except:
            pass
