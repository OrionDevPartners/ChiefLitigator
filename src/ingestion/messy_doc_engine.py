"""Messy-Doc Ingestion Engine — OCR + Email Threading + Context Mapping.

This module handles unstructured, 'real world' data:
  - Multi-modal OCR (handwritten notes, blurry faxes, screenshots) via AWS Bedrock
  - Email thread reconstruction and deduplication
  - Timeline extraction from disparate sources
  - Context mapping to legal facts
"""

import os
import json
import base64
import email
from email import policy
from typing import List, Dict, Any, Optional
from datetime import datetime
import boto3

class MessyDocEngine:
    """Engine for processing unstructured and messy legal data."""

    def __init__(self):
        self.supported_formats = [".pdf", ".jpg", ".jpeg", ".png", ".eml", ".msg", ".txt"]
        self.ocr_confidence_threshold = 0.85
        # Initialize Bedrock client for multi-modal OCR and context mapping
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=os.getenv("AWS_REGION", "us-east-1"))
        self.model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    async def process_ingestion_batch(self, case_id: str, files: List[str]) -> Dict[str, Any]:
        """Process a batch of messy documents and return a structured timeline."""
        results = {
            "case_id": case_id,
            "processed_at": datetime.utcnow().isoformat(),
            "documents": [],
            "timeline": [],
            "extracted_facts": [],
            "confidence_score": 0.0
        }

        for file_path in files:
            if os.path.exists(file_path):
                doc_result = await self._process_single_doc(file_path)
                results["documents"].append(doc_result)

        # Reconstruct timeline and extract facts
        results["timeline"] = self._reconstruct_timeline(results["documents"])
        results["extracted_facts"] = await self._map_context_to_facts(results["documents"])
        results["confidence_score"] = self._calculate_aggregate_confidence(results["documents"])

        return results

    async def _process_single_doc(self, file_path: str) -> Dict[str, Any]:
        """Process a single document based on its type."""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in [".jpg", ".jpeg", ".png", ".pdf"]:
            return await self._run_multimodal_ocr(file_path)
        elif ext in [".eml"]:
            return await self._reconstruct_email_thread(file_path)
        else:
            return await self._process_text_doc(file_path)

    async def _run_multimodal_ocr(self, file_path: str) -> Dict[str, Any]:
        """Run AWS Bedrock multi-modal OCR on images/PDFs."""
        ext = os.path.splitext(file_path)[1].lower()
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            
        media_type = "image/jpeg"
        if ext == ".png":
            media_type = "image/png"
        elif ext == ".pdf":
            media_type = "application/pdf"
            
        prompt = "Extract all text from this document. If it is handwritten, transcribe it carefully. Identify any dates, names, or key events. Output as JSON with keys: 'extracted_text', 'is_handwritten' (boolean), 'dates_found' (list), 'confidence' (float 0-1)."
        
        try:
            # For PDF, Claude 3.5 Sonnet supports document blocks. For images, image blocks.
            if media_type == "application/pdf":
                content_block = {
                    "document": {
                        "name": "document",
                        "format": "pdf",
                        "source": {"bytes": file_bytes}
                    }
                }
            else:
                content_block = {
                    "image": {
                        "format": ext.replace(".", ""),
                        "source": {"bytes": file_bytes}
                    }
                }
                
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            content_block,
                            {"text": prompt}
                        ]
                    }
                ]
            )
            
            output_text = response['output']['message']['content'][0]['text']
            # Parse JSON from output
            try:
                # Find JSON block if wrapped in markdown
                if "```json" in output_text:
                    json_str = output_text.split("```json")[1].split("```")[0].strip()
                else:
                    json_str = output_text.strip()
                parsed_data = json.loads(json_str)
            except:
                parsed_data = {
                    "extracted_text": output_text,
                    "is_handwritten": False,
                    "dates_found": [],
                    "confidence": 0.7
                }
                
            return {
                "file": file_path,
                "type": "image_pdf",
                "content": parsed_data.get("extracted_text", ""),
                "is_handwritten": parsed_data.get("is_handwritten", False),
                "dates": parsed_data.get("dates_found", []),
                "confidence": parsed_data.get("confidence", 0.85),
                "metadata": {"media_type": media_type}
            }
        except Exception as e:
            return {
                "file": file_path,
                "type": "image_pdf",
                "content": f"Error processing document: {str(e)}",
                "confidence": 0.0
            }

    async def _reconstruct_email_thread(self, file_path: str) -> Dict[str, Any]:
        """Parse email files and reconstruct the conversation thread."""
        try:
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)
                
            body = msg.get_body(preferencelist=('plain', 'html'))
            content = body.get_content() if body else ""
            
            date_str = msg.get('Date', '')
            
            return {
                "file": file_path,
                "type": "email",
                "thread_id": msg.get('Message-ID', 'unknown'),
                "participants": [msg.get('From', ''), msg.get('To', '')],
                "messages": [
                    {"date": date_str, "from": msg.get('From', ''), "body": content}
                ],
                "content": content,
                "dates": [date_str] if date_str else [],
                "confidence": 1.0
            }
        except Exception as e:
            return {
                "file": file_path,
                "type": "email",
                "content": f"Error parsing email: {str(e)}",
                "confidence": 0.0
            }

    def _reconstruct_timeline(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort all extracted events into a chronological timeline."""
        events = []
        for doc in docs:
            dates = doc.get("dates", [])
            for d in dates:
                events.append({
                    "timestamp": d,
                    "source_file": doc.get("file"),
                    "content_snippet": doc.get("content", "")[:200]
                })
        # Basic sort (assuming dates are somewhat ISO format or sortable, in reality needs NLP date parsing)
        return sorted(events, key=lambda x: x["timestamp"])

    async def _map_context_to_facts(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map document content to legal facts using Bedrock."""
        if not docs:
            return []
            
        combined_text = "\n\n".join([f"Doc: {d.get('file')}\nContent: {d.get('content')}" for d in docs])
        prompt = f"Analyze the following documents and extract key legal facts. Output a JSON list of objects with keys: 'fact', 'source_doc', 'legal_relevance'.\n\nDocuments:\n{combined_text}"
        
        try:
            response = self.bedrock_client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}]
            )
            output_text = response['output']['message']['content'][0]['text']
            if "```json" in output_text:
                json_str = output_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = output_text.strip()
            return json.loads(json_str)
        except:
            return [{"fact": "Could not extract facts automatically.", "source_doc": "all", "legal_relevance": "unknown"}]

    def _calculate_aggregate_confidence(self, docs: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence in the ingestion results."""
        if not docs: return 0.0
        return sum(d.get("confidence", 0.0) for d in docs) / len(docs)

    async def _process_text_doc(self, file_path: str) -> Dict[str, Any]:
        """Process simple text documents."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {
                "file": file_path,
                "type": "text",
                "content": content,
                "dates": [],
                "confidence": 1.0
            }
        except Exception as e:
            return {
                "file": file_path,
                "type": "text",
                "content": f"Error reading text: {str(e)}",
                "confidence": 0.0
            }
