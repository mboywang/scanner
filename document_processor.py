import os
import shutil
from pathlib import Path
import re
from scanner_log import get_logger, activity

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class DocumentProcessor:
    def __init__(self, base_folder, use_ocr=True):
        self.base_folder = base_folder
        self.log = get_logger()
        self.use_ocr = use_ocr
        self._ocr = None  # lazily created QwenOCR (heavy model)
        self.categories = self._load_categories()

    def _get_ocr(self, callback=None):
        """Lazily create the Qwen OCR engine. Returns None if unavailable."""
        if not self.use_ocr:
            return None
        if self._ocr is None:
            try:
                from qwen_ocr import QwenOCR
                self._ocr = QwenOCR(callback=callback)
            except Exception as e:
                self.log.warning("OCR unavailable: %s", e)
                self.use_ocr = False
                return None
        else:
            self._ocr.callback = callback
        return self._ocr

    def _load_categories(self):
        """Load category folders and build keyword mappings"""
        categories = {}

        if os.path.exists(self.base_folder):
            for folder in os.listdir(self.base_folder):
                folder_path = os.path.join(self.base_folder, folder)
                if os.path.isdir(folder_path):
                    categories[folder] = self._extract_keywords(folder)

        return categories

    def _extract_keywords(self, folder_name):
        """Extract keywords from folder name"""
        # Remove numbering and brackets
        name = re.sub(r'^\d+\.\s*', '', folder_name)
        name = re.sub(r'\s*\[.*?\]', '', name)

        # Split by spaces and common delimiters
        keywords = re.split(r'[\s\-_,()]', name.lower())
        keywords = [k.strip() for k in keywords if k.strip() and len(k) > 2]

        return keywords

    def extract_text_from_pdf(self, pdf_path, callback=None):
        """Extract text from PDF using pdfplumber"""
        try:
            text = ""

            # Use pdfplumber for text extraction
            if pdfplumber:
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        for page_num, page in enumerate(pdf.pages, 1):
                            page_text = page.extract_text() or ""
                            if page_text:
                                text += f"\n--- Page {page_num} ---\n{page_text}\n"

                    if text.strip():
                        if callback:
                            callback(f"Extracted text from PDF")
                        return text
                except Exception as e:
                    if callback:
                        callback(f"pdfplumber error: {e}")

            # No embedded text -> image-only scan. Fall back to OCR.
            if not text.strip():
                ocr = self._get_ocr(callback=callback)
                if ocr is not None:
                    self.log.info("No embedded text in %s - running OCR",
                                  os.path.basename(pdf_path))
                    if callback:
                        callback("No text found - running OCR...")
                    ocr_text = ocr.extract_text_from_pdf(pdf_path)
                    if ocr_text and ocr_text.strip():
                        activity(self.log,
                                 f"OCR read {len(ocr_text.strip())} chars from "
                                 f"'{os.path.basename(pdf_path)}'")
                        return ocr_text

            return text

        except Exception as e:
            if callback:
                callback(f"Error extracting text: {e}")
            return ""

    def categorize_document(self, pdf_path, callback=None):
        """Analyze content and determine best category"""
        filename = os.path.basename(pdf_path)
        text = self.extract_text_from_pdf(pdf_path, callback)

        # Score each category based on keyword matches
        scores = {}
        text_lower = text.lower()
        filename_lower = filename.lower()

        for category, keywords in self.categories.items():
            score = 0

            for keyword in keywords:
                # Match in filename (higher weight)
                if keyword in filename_lower:
                    score += 5

                # Match in content (lower weight)
                if keyword in text_lower:
                    score += 1

            if score > 0:
                scores[category] = score

        # Add heuristics based on content
        content_scores = self._apply_content_heuristics(text, filename)

        # Combine scores
        for category, score in content_scores.items():
            scores[category] = scores.get(category, 0) + score

        # Record the decision and its reasoning for human review.
        top = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:5]
        self.log.info("Categorize '%s': text=%d chars, scores=%s",
                      filename, len(text.strip()), top or "none")

        if scores:
            best_category = max(scores, key=scores.get)
            confidence = scores[best_category]

            if callback:
                callback(f"Categorized as: {best_category}")

            return best_category

        return None

    def _apply_content_heuristics(self, text, filename):
        """Apply content-based rules for categorization"""
        scores = {}
        text_lower = text.lower()

        # Tax documents
        if any(word in text_lower for word in ['tax', 'irs', 'return', '1040', '1099', 'w2', 'excise']):
            scores['2022 Tax Files'] = 3

        # Bills/Utilities/Invoices
        if any(word in text_lower for word in ['invoice', 'bill', 'amount due', 'comed', 'utility', 'payment', 'statement']):
            for category in self.categories:
                if 'jexet' in category.lower():
                    scores[category] = scores.get(category, 0) + 2

        # Personal documents
        if any(word in text_lower for word in ['personal', 'family', 'mortgage', 'loan', 'home', 'chase', 'bank']):
            for category in self.categories:
                if 'daniel personal' in category.lower():
                    scores[category] = scores.get(category, 0) + 2

        # Business/Company documents
        if any(word in text_lower for word in ['chicago computer', 'ccc', 'club', 'evergreen', 'tnm']):
            for category in self.categories:
                if any(org in category.lower() for org in ['chicago computer', 'evergreen', 'tnm']):
                    scores[category] = scores.get(category, 0) + 3

        # DONE folder - already processed
        if any(word in filename.lower() for word in ['done', 'processed']):
            scores['DONE'] = 5

        # Dump for review if uncertain
        if not scores or max(scores.values()) < 2:
            scores['Dump for Review'] = 1

        return scores

    def move_file(self, source_path, target_folder):
        """Move file to target folder"""
        try:
            target_path = os.path.join(self.base_folder, target_folder)

            if not os.path.exists(target_path):
                os.makedirs(target_path, exist_ok=True)

            # Get filename
            filename = os.path.basename(source_path)
            destination = os.path.join(target_path, filename)

            # Handle duplicates
            if os.path.exists(destination):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(destination):
                    destination = os.path.join(target_path, f"{base}_{counter}{ext}")
                    counter += 1

            # Move file
            shutil.move(source_path, destination)
            return destination

        except Exception as e:
            raise Exception(f"Error moving file: {e}")

    def process_file(self, pdf_path, auto_move=True, callback=None):
        """Process a single PDF file"""
        try:
            filename = os.path.basename(pdf_path)

            if callback:
                callback(f"Processing {filename}...")

            # Categorize
            category = self.categorize_document(pdf_path, callback)

            if not category:
                activity(self.log, f"PROCESS could not categorize '{filename}' (left in place)")
                if callback:
                    callback(f"Could not categorize {filename}")
                return False

            # Move file
            if auto_move:
                destination = self.move_file(pdf_path, category)
                note = " (no confident match)" if category == 'Dump for Review' else ""
                activity(self.log, f"MOVED '{filename}' -> {category}{note}")
                self.log.debug("Destination: %s", destination)
                if callback:
                    callback(f"Moved to: {category}")

            return True

        except Exception as e:
            activity(self.log, f"PROCESS ERROR on '{os.path.basename(pdf_path)}': {e}")
            if callback:
                callback(f"Error processing file: {e}")
            return False

    def process_folder(self, folder_path, callback=None):
        """Process all PDF files in a folder"""
        try:
            files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]

            if not files:
                if callback:
                    callback("No PDF files found")
                return 0

            if callback:
                callback(f"Found {len(files)} files to process...")

            processed = 0
            for filename in files:
                filepath = os.path.join(folder_path, filename)

                if self.process_file(filepath, auto_move=True, callback=callback):
                    processed += 1

            if callback:
                callback(f"Processed {processed}/{len(files)} files")

            return processed

        except Exception as e:
            if callback:
                callback(f"Error processing folder: {e}")
            return 0
