from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from typing import Dict, List
import logging
import os


class MedicalReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            "CustomTitle",
            parent=self.styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor("#1e3d59"),  # Deep blue
            alignment=1,  # Center
        )

        self.section_header = ParagraphStyle(
            "SectionHeader",
            parent=self.styles["Heading2"],
            fontSize=16,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor("#17a2b8"),  # Teal
        )

        self.event_date_style = ParagraphStyle(
            "EventDate",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#6c757d"),  # Gray
            spaceBefore=15,
        )

        self.event_content_style = ParagraphStyle(
            "EventContent",
            parent=self.styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#2c3e50"),  # Dark blue-gray
            leftIndent=20,
            spaceBefore=5,
        )

        self.event_type_style = ParagraphStyle(
            "EventType",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#28a745"),  # Green
            leftIndent=20,
            spaceBefore=2,
        )

    def _get_date_range(self, events: List[Dict]) -> str:
        """Calculate date range of medical history"""
        if not events:
            return "No events recorded"

        dates = [event.get("date", "") for event in events if event.get("date")]
        if dates:
            earliest = min(dates)[:10]
            latest = max(dates)[:10]
            return f"{earliest} to {latest}"
        return "Date range unavailable"

    def _clean_content(self, content: str) -> str:
        """Clean and format content text"""
        if "**" in content:
            # Remove markdown
            clean_text = content.replace("**", "")

            # Get meaningful content
            relevant_lines = []
            for line in clean_text.split("\n"):
                line = line.strip()
                if line and not line.endswith(":") and not line.startswith("*"):
                    if (
                        "General Content:" not in line
                        and "Medical Relevance:" not in line
                    ):
                        relevant_lines.append(line)

            return " ".join(relevant_lines)
        return content

    def _format_date(self, date_str: str) -> str:
        """Format date string to readable format"""
        try:
            if isinstance(date_str, str) and len(date_str) > 10:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                return dt.strftime("%B %d, %Y")  # More readable date format
            return date_str
        except Exception:
            return "Date not available"

    def generate_report(self, medical_data: Dict, phone_number: str) -> str:
        """Generate comprehensive PDF report from medical history"""
        try:
            os.makedirs("reports", exist_ok=True)
            filename = f"reports/medical_report_{phone_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            doc = SimpleDocTemplate(
                filename,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )

            story = []

            # Title
            story.append(
                Paragraph(
                    "HealthBook - Your comprehensive Medical History Report",
                    self.title_style,
                )
            )
            story.append(Spacer(1, 30))

            # Executive Summary
            story.append(Paragraph("Executive Summary", self.section_header))
            summary_items = [
                f"Patient ID: {phone_number}",
                f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"Total Records: {len(medical_data.get('chronological_events', []))}",
                f"Date Range: {self._get_date_range(medical_data.get('chronological_events', []))}",
            ]
            for item in summary_items:
                story.append(Paragraph(item, self.event_content_style))
            story.append(Spacer(1, 20))

            # Active Medical Conditions
            if medical_data.get("conditions"):
                story.append(
                    Paragraph("Active Medical Conditions", self.section_header)
                )
                for condition in set(medical_data["conditions"]):
                    story.append(Paragraph(f"• {condition}", self.event_content_style))
                story.append(Spacer(1, 15))

            # Current Medications
            if medical_data.get("medications"):
                story.append(Paragraph("Current Medications", self.section_header))
                for medication in set(medical_data["medications"]):
                    story.append(Paragraph(f"• {medication}", self.event_content_style))
                story.append(Spacer(1, 15))

            # Symptoms
            if medical_data.get("symptoms"):
                story.append(Paragraph("Reported Symptoms", self.section_header))
                for symptom in set(medical_data["symptoms"]):
                    story.append(Paragraph(f"• {symptom}", self.event_content_style))
                story.append(Spacer(1, 15))

            # Body Parts
            if medical_data.get("body_parts"):
                story.append(Paragraph("Affected Areas", self.section_header))
                for body_part in set(medical_data["body_parts"]):
                    story.append(Paragraph(f"• {body_part}", self.event_content_style))
                story.append(Spacer(1, 15))

            # Medical Timeline
            if medical_data.get("chronological_events"):
                story.append(Paragraph("Medical Timeline", self.section_header))
                story.append(Spacer(1, 10))

                # Sort events by date
                sorted_events = sorted(
                    medical_data["chronological_events"],
                    key=lambda x: x.get("date", "0"),
                    reverse=True,
                )

                for event in sorted_events:
                    # Date
                    date = self._format_date(event.get("date", "N/A"))
                    story.append(Paragraph(f"📅 {date}", self.event_date_style))

                    # Content
                    content = self._clean_content(event.get("content", "N/A"))
                    story.append(Paragraph(content, self.event_content_style))

                    # Event Type
                    event_type = event.get("type", "general").capitalize()
                    story.append(
                        Paragraph(f"Type: {event_type}", self.event_type_style)
                    )

                    # Add a divider line
                    story.append(
                        Paragraph(
                            "<para><font color='#e9ecef'>_"
                            + "_" * 50
                            + "</font></para>",
                            self.styles["Normal"],
                        )
                    )

            # Build the PDF
            doc.build(story)
            return filename

        except Exception as e:
            logging.error(f"Error generating PDF report: {e}")
            raise
