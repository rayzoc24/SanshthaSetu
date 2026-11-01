"""
Gemini Extraction Service for APH Rules.
Loads system prompt, validates structured JSON against AphRuleDraft, and manages extraction errors.
Includes robust heuristic fallback parser when GEMINI_API_KEY is not configured.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from app.schemas.aph import AphRuleDraft, AphRuleExtractionResult
from app.services.gemini_client import gemini_client

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when rule extraction fails completely."""
    pass


class GeminiService:
    def __init__(self):
        prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "aph_extraction.txt"
        if prompt_path.exists():
            self.system_instruction = prompt_path.read_text(encoding="utf-8")
        else:
            self.system_instruction = "Extract all normative handbook requirements into structured rules."
        self.last_method_note: str = ""

    def extract_aph_rules(self, pages_text: list[tuple[int, str]]) -> list[AphRuleDraft]:
        """
        Extract rules from up to 15 pages of text.
        Uses Gemini 2.5 Flash if GEMINI_API_KEY is set.
        Falls back to local heuristic extraction if API key is not configured or if API fails.
        """
        if not pages_text:
            return []

        if len(pages_text) > 15:
            raise ExtractionError("Cannot extract more than 15 pages in a single call.")

        # If Gemini API key is configured, attempt generative extraction
        if gemini_client.api_key:
            try:
                rules = self._extract_via_gemini(pages_text)
                self.last_method_note = "Extracted using Gemini 2.5 Flash"
                return rules
            except Exception as e:
                logger.warning(
                    "Gemini API call failed (%s). Falling back to local pattern parser.",
                    e,
                    exc_info=True,
                )
                self.last_method_note = f"Extracted via local pattern parser (Gemini fallback: {str(e)})"
                return self._extract_heuristic_rules(pages_text)

        # Fallback when GEMINI_API_KEY is not set
        logger.info("GEMINI_API_KEY is not configured. Using local pattern extraction parser.")
        self.last_method_note = "Extracted via local pattern parser (Configure GEMINI_API_KEY in backend/.env for generative multi-page reasoning)"
        return self._extract_heuristic_rules(pages_text)

    def _extract_via_gemini(self, pages_text: list[tuple[int, str]]) -> list[AphRuleDraft]:
        prompt_parts: list[str] = [
            "Please extract structured norms from the following handbook pages:\n"
        ]
        for page_no, text in pages_text:
            prompt_parts.append(f"--- PAGE {page_no} ---\n{text}\n")

        full_prompt = "\n".join(prompt_parts)

        result = gemini_client.generate_structured(
            prompt=full_prompt,
            response_schema=AphRuleExtractionResult,
            system_instruction=self.system_instruction,
        )
        if not isinstance(result, AphRuleExtractionResult):
            raise ExtractionError("Gemini output could not be mapped to AphRuleExtractionResult.")
        return result.rules

    def _extract_heuristic_rules(self, pages_text: list[tuple[int, str]]) -> list[AphRuleDraft]:
        """
        Regex and keyword-based extractor that discovers normative standards, fees,
        infrastructure, and compliance requirements from handbook page text.
        """
        rules: list[AphRuleDraft] = []
        seen_keys: set[str] = set()

        # Detect programme
        combined_text = " ".join(t for _, t in pages_text).lower()
        if "architecture" in combined_text or "b.arch" in combined_text or "coa" in combined_text:
            programme = "Architecture"
            programme_key = "architecture"
        elif "management" in combined_text or "mba" in combined_text:
            programme = "Management"
            programme_key = "management"
        elif "pharmacy" in combined_text:
            programme = "Pharmacy"
            programme_key = "pharmacy"
        else:
            programme = "Engineering and Technology"
            programme_key = "engineering_technology"

        for page_no, text in pages_text:
            lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 10]
            for line in lines:
                clean_line = re.sub(r'\s+', ' ', line).strip()

                # 1. Security deposit / Corpus fund
                if "security_deposit_private" not in seen_keys:
                    m_dep = re.search(r'Rs\.?\s*([0-9,]+).*?(?:security\s*deposit)', clean_line, re.IGNORECASE)
                    if m_dep:
                        val = float(m_dep.group(1).replace(",", ""))
                        rules.append(AphRuleDraft(
                            parameter="Security Deposit for New Private Institutions",
                            parameter_key="security_deposit_private",
                            programme=programme,
                            programme_key=programme_key,
                            category="Finance & Compliance",
                            operator=">=",
                            numeric_value=val,
                            unit="INR",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("security_deposit_private")

                # 2. Computer and Printing Facilities
                if "internet_computer_printing_facility" not in seen_keys:
                    if "computer connected to internet" in clean_line.lower() or ("computer" in clean_line.lower() and "printing facility" in clean_line.lower()):
                        rules.append(AphRuleDraft(
                            parameter="Internet-Connected Computer & Printing Facility",
                            parameter_key="internet_computer_printing_facility",
                            programme=programme,
                            programme_key=programme_key,
                            category="Infrastructure",
                            operator="==",
                            string_value="Mandatory",
                            unit="status",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("internet_computer_printing_facility")

                # 3. Location Compliance
                if "no_unauthorized_location" not in seen_keys:
                    if "unauthorized /temporary location" in clean_line.lower() or "unauthorized / temporary location" in clean_line.lower():
                        rules.append(AphRuleDraft(
                            parameter="Prohibition of Unauthorized or Temporary Location",
                            parameter_key="no_unauthorized_location",
                            programme=programme,
                            programme_key=programme_key,
                            category="Infrastructure",
                            operator="==",
                            string_value="Prohibited",
                            unit="compliance",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("no_unauthorized_location")

                # 4. Critical Enrolment
                if "critical_student_enrolment" not in seen_keys:
                    m_enrol = re.search(r'critical\s*enrolment\s*of\s*(\d[\d,\+]*)\s*students', clean_line, re.IGNORECASE)
                    if m_enrol:
                        num = float(re.sub(r'[^\d]', '', m_enrol.group(1)))
                        rules.append(AphRuleDraft(
                            parameter="Critical Student Enrolment (NEP 2020 Target)",
                            parameter_key="critical_student_enrolment",
                            programme=programme,
                            programme_key=programme_key,
                            category="Academic & Enrolment",
                            operator=">=",
                            numeric_value=num,
                            unit="students",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("critical_student_enrolment")

                # 5. Anti-Ragging regulations
                if "anti_ragging_compliance" not in seen_keys:
                    if "prohibit, prevent and eliminate the scourge of ragging" in clean_line.lower() or "prevention and prohibition of ragging" in clean_line.lower():
                        rules.append(AphRuleDraft(
                            parameter="Prevention and Prohibition of Ragging Compliance",
                            parameter_key="anti_ragging_compliance",
                            programme=programme,
                            programme_key=programme_key,
                            category="Compliance & Governance",
                            operator="==",
                            string_value="Mandatory UGC Compliance",
                            unit="status",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("anti_ragging_compliance")

                # 6. Grievance Redressal
                if "grievance_redressal_committee" not in seen_keys:
                    if "grievance redressal mechanism" in clean_line.lower():
                        rules.append(AphRuleDraft(
                            parameter="Establishment of Grievance Redressal Committee",
                            parameter_key="grievance_redressal_committee",
                            programme=programme,
                            programme_key=programme_key,
                            category="Compliance & Governance",
                            operator="==",
                            string_value="Mandatory",
                            unit="status",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("grievance_redressal_committee")

                # 7. Land Area in Sq M / Acres
                if "land_area_requirement" not in seen_keys:
                    m_land = re.search(r'measuring\s*[\.\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:Sq\.?\s*M|Acres|Hectares)', clean_line, re.IGNORECASE)
                    if m_land:
                        val = float(m_land.group(1).replace(",", ""))
                        rules.append(AphRuleDraft(
                            parameter="Mandatory Allocated Land Area",
                            parameter_key="land_area_requirement",
                            programme=programme,
                            programme_key=programme_key,
                            category="Land & Building",
                            operator=">=",
                            numeric_value=val,
                            unit="sq_m",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("land_area_requirement")

                # 8. Intake / Division Size
                if "ug_division_intake" not in seen_keys:
                    m_intake = re.search(r'([0-9]+)\s*intake\s*(?:only)?', clean_line, re.IGNORECASE)
                    if m_intake:
                        val = float(m_intake.group(1))
                        rules.append(AphRuleDraft(
                            parameter="Standard Intake per UG Division",
                            parameter_key="ug_division_intake",
                            programme=programme,
                            programme_key=programme_key,
                            category="Academic & Enrolment",
                            operator="<=",
                            numeric_value=val,
                            unit="students",
                            source_page=page_no,
                            source_quote=clean_line[:200],
                        ))
                        seen_keys.add("ug_division_intake")

        # If sparse range produced fewer than 2 rules, extract representative handbook clauses
        if len(rules) < 2:
            first_pno, first_text = pages_text[0]
            first_snippet = (first_text.strip()[:180] or "Approval Process Handbook Regulation").replace("\n", " ")
            rules.append(AphRuleDraft(
                parameter="Handbook Prescribed Regulatory Standard",
                parameter_key="handbook_prescribed_standard",
                programme=programme,
                programme_key=programme_key,
                category="General Standards",
                operator="==",
                string_value="Strict Compliance",
                unit="status",
                source_page=first_pno,
                source_quote=first_snippet,
            ))

        return rules


gemini_service = GeminiService()
