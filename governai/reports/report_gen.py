import os
import sys
# Add the governai folder to the Python path so it can resolve database/services modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from database.db import SessionLocal
from services.ai_system_svc import get_system_by_id
from services.compliance_svc import get_compliance_score

def generate_pdf_report(system_id: str, output_path: str):
    """Generates an auditor-ready PDF report for a given AI system."""
    db = SessionLocal()
    system = get_system_by_id(db, system_id)
    
    if not system:
        db.close()
        raise ValueError("System not found")
        
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    story.append(Paragraph(f"AI Governance Audit Report: {system.name}", title_style))
    story.append(Spacer(1, 20))
    
    # Overview
    story.append(Paragraph("System Overview", styles['Heading2']))
    story.append(Paragraph(f"<b>Owner:</b> {system.owner}", styles['Normal']))
    story.append(Paragraph(f"<b>Business Purpose:</b> {system.business_purpose}", styles['Normal']))
    story.append(Paragraph(f"<b>Model Type:</b> {system.model_type} ({system.model_source})", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Risk & Compliance
    story.append(Paragraph("Risk & Compliance Status", styles['Heading2']))
    story.append(Paragraph(f"<b>EU AI Act Risk Tier:</b> {system.risk_tier}", styles['Normal']))
    story.append(Paragraph(f"<b>Current Status:</b> {system.compliance_status}", styles['Normal']))
    
    score_eu = get_compliance_score(db, system_id, "EU AI Act")
    score_nist = get_compliance_score(db, system_id, "NIST AI RMF")
    story.append(Paragraph(f"<b>EU AI Act Completeness:</b> {score_eu}%", styles['Normal']))
    story.append(Paragraph(f"<b>NIST AI RMF Completeness:</b> {score_nist}%", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Risk Assessment Details (if available)
    if system.risk_assessments and system.risk_assessments[0].answers:
        story.append(Paragraph("Risk Assessment Responses", styles['Heading2']))
        assessment = system.risk_assessments[0]
        story.append(Paragraph(f"<b>Assessed By:</b> {assessment.assessed_by} on {assessment.assessed_at.split('T')[0]}", styles['Normal']))
        story.append(Spacer(1, 10))
        
        q_data = [["Question Key", "Answer", "Weight"]]
        for ans in assessment.answers:
            q_data.append([ans.question_key, ans.answer, str(ans.weight)])
            
        t_risk = Table(q_data, colWidths=[300, 100, 50])
        t_risk.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4a4e69")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        story.append(t_risk)
        story.append(Spacer(1, 15))
    
    # Data Sources
    story.append(Paragraph("Data Sources & Privacy", styles['Heading2']))
    if system.data_sources:
        ds_data = [["Source Name", "Contains PII?", "Categories"]]
        for ds in system.data_sources:
            ds_data.append([ds.source_name, "Yes" if ds.contains_pii else "No", ds.pii_categories or "N/A"])
        t = Table(ds_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No data sources registered.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Audit Trail
    story.append(Paragraph("Recent Audit Trail", styles['Heading2']))
    if system.audit_logs:
        audit_data = [["Timestamp", "User", "Action"]]
        for log in system.audit_logs[:10]:
            audit_data.append([log.timestamp.split('T')[0], log.user, log.action])
        
        t2 = Table(audit_data)
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(t2)
    else:
        story.append(Paragraph("No audit logs available.", styles['Normal']))
        
    doc.build(story)
    db.close()
    return output_path

if __name__ == "__main__":
    # Test generation
    db = SessionLocal()
    sys = db.query(AISystem).first()
    if sys:
        generate_pdf_report(sys.id, "test_report.pdf")
        print("Generated test_report.pdf")
    db.close()
