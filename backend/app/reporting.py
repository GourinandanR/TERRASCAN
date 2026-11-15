"""Evidence-backed report builders. Never infer or manufacture missing scientific values."""
from __future__ import annotations
import csv, io, json
from datetime import datetime, timezone
from typing import Any

FEATURE_LABELS = {
    "slope": "Slope distribution", "roughness": "Surface roughness",
    "thermal": "Thermal environment", "elevationRange": "Elevation range",
    "geology": "Geological class",
}

def collect_report_data(conn, target_body: str) -> dict[str, Any]:
    observations = [dict(r) for r in conn.execute("""
        SELECT o.*, m.dataset_id, m.version AS manifest_version, m.sha256,
               m.source_uri, m.review_status AS manifest_review_status,
               m.payload_json AS manifest_metadata
        FROM observations o JOIN dataset_manifests m ON m.id=o.manifest_id
        WHERE o.target_body='Earth' AND o.review_status='approved'
          AND m.review_status='approved'
        ORDER BY o.site_id, o.criterion, o.created_at
    """)]
    references = [dict(r) for r in conn.execute("""
        SELECT * FROM target_profiles WHERE target_body=? ORDER BY feature_key
    """, (target_body,))]
    manifests = [dict(r) for r in conn.execute("""
        SELECT * FROM dataset_manifests WHERE review_status='approved'
        ORDER BY dataset_id, version
    """)]
    pending = conn.execute("""
        SELECT
          (SELECT COUNT(*) FROM dataset_manifests WHERE review_status='pending-human-review') AS pending_manifests,
          (SELECT COUNT(*) FROM observations WHERE review_status='pending-human-review') AS pending_observations,
          (SELECT COUNT(*) FROM observations WHERE review_status='rejected') AS rejected_observations
    """).fetchone()
    return {
        "schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_body": target_body, "observations": observations,
        "target_references": references, "approved_manifests": manifests,
        "review_queue": dict(pending),
        "comparison_status": "not-computed",
        "interpretation": "This report summarizes reviewed records. No similarity scores, ranks, or mission suitability conclusions are computed by the reporting service."
    }

def build_csv(data: dict[str, Any]) -> str:
    out = io.StringIO(newline="")
    fields = ["site_id","criterion","feature_label","value","unit","quality","observation_review_status",
              "reviewer","reviewed_at","manifest_id","dataset_id","manifest_version","sha256","source_uri"]
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in data["observations"]:
        writer.writerow({**row, "feature_label": FEATURE_LABELS.get(row["criterion"], row["criterion"])})
    return out.getvalue()

def build_pdf(data: dict[str, Any]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except ImportError as exc:
        raise RuntimeError("PDF export requires reportlab. Install backend/requirements.txt.") from exc
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=17*mm, bottomMargin=17*mm, title="TERRASCAN Scientific Evidence Report")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallCell", parent=styles["BodyText"], fontSize=7, leading=9))
    story = [
        Paragraph("TERRASCAN", styles["Title"]),
        Paragraph(f"Scientific Evidence Report — Earth analogs vs {data['target_body']}", styles["Heading2"]),
        Paragraph(f"Generated: {data['generated_at']}", styles["BodyText"]),
        Spacer(1, 8*mm),
        Paragraph("Executive summary", styles["Heading2"]),
        Paragraph(f"Approved Earth observations: {len(data['observations'])}. Approved source manifests: {len(data['approved_manifests'])}. Target reference records: {len(data['target_references'])}.", styles["BodyText"]),
        Paragraph("Comparison status: NOT COMPUTED. This report does not contain similarity scores, rankings, or mission suitability conclusions.", styles["BodyText"]),
        Spacer(1, 4*mm),
        Paragraph("Data quality and review status", styles["Heading2"]),
        Paragraph(f"Pending manifests: {data['review_queue']['pending_manifests']}; pending observations: {data['review_queue']['pending_observations']}; rejected observations: {data['review_queue']['rejected_observations']}.", styles["BodyText"]),
        Paragraph("Approved records are included only when both the observation and its source manifest are approved.", styles["BodyText"]),
        Spacer(1, 4*mm),
        Paragraph("Approved scientific observations", styles["Heading2"]),
    ]
    rows = [["Site", "Feature", "Value", "Unit", "Quality", "Dataset / SHA-256"]]
    for r in data["observations"]:
        rows.append([
            Paragraph(str(r["site_id"]), styles["SmallCell"]),
            Paragraph(FEATURE_LABELS.get(r["criterion"], str(r["criterion"])), styles["SmallCell"]),
            Paragraph(str(r["value"]), styles["SmallCell"]),
            Paragraph(str(r["unit"]), styles["SmallCell"]),
            Paragraph(str(r["quality"]), styles["SmallCell"]),
            Paragraph(f"{r['dataset_id']}<br/>{r['sha256']}", styles["SmallCell"])
        ])
    if len(rows) == 1: rows.append([Paragraph("No approved observations available.", styles["SmallCell"]), "", "", "", "", ""])
    table = Table(rows, colWidths=[24*mm,29*mm,17*mm,14*mm,20*mm,70*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173449")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#bdc9d2")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),7),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f1f5f7")]),
        ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)
    ]))
    story += [table, Spacer(1,5*mm), Paragraph("Approved target reference records", styles["Heading2"])]
    ref_rows = [["Feature key","Value","Unit","Metadata"]]
    for r in data["target_references"]:
        ref_rows.append([str(r["feature_key"]),str(r["value"]),str(r["unit"]),str(r.get("payload_json",""))[:180]])
    if len(ref_rows)==1: ref_rows.append(["No target reference records available.","","",""])
    rt=Table(ref_rows,colWidths=[35*mm,25*mm,20*mm,94*mm],repeatRows=1)
    rt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173449")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
                            ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#bdc9d2")),("FONTSIZE",(0,0),(-1,-1),7),
                            ("VALIGN",(0,0),(-1,-1),"TOP")]))
    story += [rt, Spacer(1,5*mm), Paragraph("Provenance and methodology",styles["Heading2"])]
    for m in data["approved_manifests"]:
        story.append(Paragraph(f"{m['dataset_id']} · v{m['version']} · SHA-256 {m['sha256']} · {m['source_uri']}", styles["SmallCell"]))
    story += [Spacer(1,3*mm), Paragraph(data["interpretation"],styles["BodyText"]),
              Paragraph("Feature definitions, units, temporal comparability, coordinate reference systems, uncertainty and processing methods require scientific interpretation against the official source product documentation. Approval records the review workflow decision; it is not a guarantee of scientific correctness.",styles["BodyText"])]
    doc.build(story)
    return out.getvalue()
