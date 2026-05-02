import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from PIL import Image
import pdf2image
import os

class QwenOCR:
    def __init__(self, callback=None):
        self.callback = callback
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self._initialize_model()

    def _initialize_model(self):
        """Load Qwen2-VL model on first use"""
        if self.model is not None:
            return

        if self.callback:
            self.callback("Loading Qwen2-VL-7B model...")

        try:
            model_id = "Qwen/Qwen2-VL-7B-Instruct"

            if self.callback:
                self.callback("Downloading model (first time ~8GB)...")

            self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )

            if self.callback:
                self.callback(f"Model ready on {self.device.upper()}")

        except Exception as e:
            if self.callback:
                self.callback(f"Error loading model: {e}")
            raise

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using Qwen Vision"""
        try:
            if self.callback:
                self.callback("Converting PDF to images...")

            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path, dpi=200)

            if not images:
                if self.callback:
                    self.callback("No images extracted from PDF")
                return ""

            if self.callback:
                self.callback(f"Extracting text from {len(images)} page(s)...")

            all_text = ""

            for page_num, image in enumerate(images, 1):
                if self.callback:
                    self.callback(f"OCR page {page_num}/{len(images)}...")

                text = self._extract_text_from_image(image)
                if text:
                    all_text += f"\n--- Page {page_num} ---\n{text}\n"

            return all_text

        except Exception as e:
            if self.callback:
                self.callback(f"Error in PDF processing: {e}")
            return ""

    def _extract_text_from_image(self, image):
        """Extract text from a single image using Qwen"""
        try:
            # Ensure image is RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Prepare the prompt
            prompt = "Extract all text from this image. Be thorough and preserve the layout."

            # Create message
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]

            # Apply chat template
            text_input = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

            # Process inputs
            image_inputs, video_inputs = self.processor.process_images_and_videos([image])

            # Tokenize and create input dict
            inputs = self.processor(
                text=[text_input],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            )

            # Move to device
            inputs = inputs.to(self.device)

            # Generate
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=1024,
                    temperature=0.7
                )

            # Decode
            response = self.processor.batch_decode(
                output_ids,
                skip_special_tokens=True
            )[0]

            # Extract just the response part
            if "assistant\n" in response:
                response = response.split("assistant\n")[-1].strip()
            elif "<|im_end|>" in response:
                response = response.split("<|im_end|>")[0].strip()

            return response

        except Exception as e:
            if self.callback:
                self.callback(f"Image processing error: {e}")
            return ""
