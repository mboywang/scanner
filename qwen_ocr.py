"""
OCR for image-only scans using a Qwen2-VL vision-language model.

Notes for this machine:
  * torch is CPU-only here (no CUDA). The 7B model needs ~28GB RAM and is very
    slow on CPU, so the default is the 2B model (~4.5GB download) which is
    practical on CPU. Override with the SCANNER_QWEN_MODEL env var or the
    model_id argument if you have a GPU and want 7B.
  * PDF pages are rasterized with pypdfium2 (no Poppler needed).
"""
import os

# Default to the 2B model - runnable on CPU. Set SCANNER_QWEN_MODEL to
# "Qwen/Qwen2-VL-7B-Instruct" if you have a GPU / lots of RAM.
DEFAULT_MODEL_ID = os.environ.get("SCANNER_QWEN_MODEL", "Qwen/Qwen2-VL-2B-Instruct")


class QwenOCR:
    def __init__(self, callback=None, model_id=None):
        self.callback = callback
        self.model_id = model_id or DEFAULT_MODEL_ID
        self.model = None
        self.processor = None
        self.device = None

    def _log(self, msg):
        if self.callback:
            self.callback(msg)

    def _initialize_model(self):
        """Load the model on first use (lazy - avoids the big download until
        OCR is actually needed)."""
        if self.model is not None:
            return

        # Import heavy deps lazily so the app runs fine without them installed.
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._log(f"Loading {self.model_id} on {self.device.upper()} (first run downloads the model)...")

        # Cap image resolution the model sees (in 28x28 patch units) so a
        # high-DPI scan doesn't explode into tens of thousands of vision tokens.
        # ~1MP is plenty to read document text and keeps inference fast.
        self.processor = AutoProcessor.from_pretrained(
            self.model_id,
            trust_remote_code=True,
            min_pixels=256 * 28 * 28,
            max_pixels=1280 * 28 * 28,
        )
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True,
        )
        if self.device == "cpu":
            self.model = self.model.to("cpu")
        self.model.eval()
        self._log(f"Model ready on {self.device.upper()}")

    def _pdf_to_images(self, pdf_path, dpi=200):
        """Rasterize every PDF page to a PIL image using pypdfium2 (no Poppler)."""
        import pypdfium2 as pdfium
        images = []
        pdf = pdfium.PdfDocument(pdf_path)
        try:
            for i in range(len(pdf)):
                page = pdf[i]
                pil = page.render(scale=dpi / 72).to_pil()
                if pil.mode != "RGB":
                    pil = pil.convert("RGB")
                images.append(pil)
        finally:
            pdf.close()
        return images

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from a PDF's page images using Qwen2-VL."""
        try:
            self._initialize_model()

            self._log("Converting PDF to images...")
            images = self._pdf_to_images(pdf_path)
            if not images:
                self._log("No images extracted from PDF")
                return ""

            self._log(f"Extracting text from {len(images)} page(s)...")
            all_text = ""
            for page_num, image in enumerate(images, 1):
                self._log(f"OCR page {page_num}/{len(images)}...")
                text = self._extract_text_from_image(image)
                if text:
                    all_text += f"\n--- Page {page_num} ---\n{text}\n"
            return all_text

        except Exception as e:
            self._log(f"OCR error: {e}")
            return ""

    # Fields we ask the model to pull out, matching the finance Excel columns.
    FIELD_KEYS = [
        "sender_name", "addressed_to", "letter_date", "due_date",
        "amount_due", "entity", "description", "tasks",
    ]

    def extract_fields(self, pdf_path, callback=None, max_pages=3):
        """
        Read a scanned PDF and extract the structured fields the finance team's
        Excel log needs, in a single vision pass per document (fast).
        Returns a dict with FIELD_KEYS (missing values as '').
        """
        if callback:
            self.callback = callback
        self._initialize_model()
        self._log("Converting PDF to images...")
        images = self._pdf_to_images(pdf_path, dpi=150)
        if not images:
            return {k: "" for k in self.FIELD_KEYS}
        # Downscale and use the first few pages - key info (sender, amount,
        # dates) is almost always on the opening pages of a letter.
        images = [self._downscale(im, 1600) for im in images[:max_pages]]
        self._log(f"Reading {len(images)} page(s) and extracting fields...")
        return self._vision_extract_fields(images)

    @staticmethod
    def _downscale(img, max_side):
        """Shrink an image so its longest side is <= max_side (keeps aspect)."""
        w, h = img.size
        if max(w, h) <= max_side:
            return img
        scale = max_side / float(max(w, h))
        return img.resize((max(1, int(w * scale)), max(1, int(h * scale))))

    def _vision_extract_fields(self, images):
        """One vision-language pass: read the page image(s) -> structured JSON."""
        import torch

        instruction = (
            "You are helping a finance team log scanned mail. Read the document "
            "image(s) and return ONLY a JSON object with these exact keys:\n"
            '- "sender_name": the company/person who SENT the letter (the letterhead/return address).\n'
            '- "addressed_to": the RECIPIENT the letter is addressed to (the "Dear ..." or mailing name). '
            "This must be different from the sender.\n"
            '- "letter_date": the date printed on the letter, formatted strictly as MM/DD/YYYY.\n'
            '- "due_date": payment or response deadline formatted MM/DD/YYYY, or "" if none.\n'
            '- "amount_due": the amount owed, including currency symbol, e.g. "$400.00", or "" if none.\n'
            '- "entity": which business or person this document concerns (often the recipient).\n'
            '- "description": one clear sentence summarizing what the document is.\n'
            '- "tasks": a concrete action for finance to take, e.g. '
            '"Pay $400.00 to Illinois DOR by 07/31/2026" or "Review and file". '
            "Do NOT copy marketing or FAQ text from the page. Use \"Review and file\" if no action is needed.\n"
            'Use "" for any field not present. Dates must be MM/DD/YYYY. '
            "Return only the JSON object, nothing else."
        )
        content = [{"type": "image", "image": im} for im in images]
        content.append({"type": "text", "text": instruction})
        messages = [{"role": "user", "content": content}]

        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(
            text=[text_input], images=images, padding=True, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs, max_new_tokens=512, do_sample=False
            )
        trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        response = self.processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        fields = self._parse_json(response)
        return {k: str(fields.get(k, "") or "").strip() for k in self.FIELD_KEYS}

    def _extract_structured_from_text(self, text):
        """Ask the model to turn OCR text into a structured JSON record."""
        import json
        import torch

        # Keep the prompt bounded - the first part of a letter carries the
        # sender / recipient / amount / dates we need.
        snippet = text.strip()[:6000]
        instruction = (
            "You are helping a finance team log scanned mail. From the document "
            "text below, return ONLY a JSON object with these exact keys:\n"
            '"sender_name" (who sent it), "addressed_to" (recipient/person or company), '
            '"letter_date" (date on the letter, MM/DD/YYYY or as written), '
            '"due_date" (payment/response deadline if any, else ""), '
            '"amount_due" (money owed with currency, e.g. "$400.00", else ""), '
            '"entity" (which business/person this concerns), '
            '"description" (one clear sentence summarizing the document), '
            '"tasks" (a short suggested action for finance, else ""). '
            'Use "" for anything not present. Return only the JSON, no other text.\n\n'
            "DOCUMENT TEXT:\n" + snippet
        )
        messages = [{"role": "user", "content": [{"type": "text", "text": instruction}]}]
        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(text=[text_input], return_tensors="pt").to(self.device)
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=512)
        trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        response = self.processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0].strip()

        fields = self._parse_json(response)
        # Guarantee every expected key exists.
        result = {k: str(fields.get(k, "") or "").strip() for k in self.FIELD_KEYS}
        # Always keep the raw OCR text available as a fallback description.
        if not result["description"]:
            result["description"] = text.strip()[:300]
        return result

    @staticmethod
    def _parse_json(response):
        """Best-effort extraction of a JSON object from model output."""
        import json
        import re
        # Strip code fences if present.
        cleaned = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # Fall back to the first {...} block.
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
        return {}

    def _extract_text_from_image(self, image):
        """Extract text from a single PIL image using Qwen2-VL."""
        import torch

        if image.mode != "RGB":
            image = image.convert("RGB")

        prompt = "Extract all text from this image. Be thorough and preserve the layout."
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        # Build the text prompt from the chat template.
        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        # Pass the PIL image directly - no qwen_vl_utils / process_vision_info
        # needed since we already hold the image object.
        inputs = self.processor(
            text=[text_input],
            images=[image],
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=1024)

        # Trim the prompt tokens so we decode only the generated answer.
        trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        response = self.processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        return response.strip()
