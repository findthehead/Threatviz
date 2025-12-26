def render_security_report_html(report: dict) -> str:
    """
    Renders a security report JSON into HTML.
    Each section (Executive Summary, Detailed Analysis, Risk Assessment, Threat Model, Mitigation)
    is rendered in its own block. Lists and numbered items are converted to HTML <li>.
    Mermaid diagrams are rendered properly.
    """
    def normalize_text_field(field):
        """Convert string or list into clean list of lines."""
        lines = []
        if isinstance(field, str):
            lines = [line.strip() for line in field.splitlines() if line.strip()]
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, str):
                    lines.extend([line.strip() for line in item.splitlines() if line.strip()])
                else:
                    lines.append(str(item).strip())
        return lines

    def generate_list(items):
        html = ""
        inside_list = False
        for item in items:
            if item and item[0].isdigit():
                if inside_list:
                    html += "</ul>\n"
                    inside_list = False
                html += f"<p>{item}</p>\n"
            elif item.lower().startswith(("i.", "ii.", "iii.", "iv.", "v.", "vi.", "vii.", "viii.", "ix.", "x.")):
                if not inside_list:
                    html += "<ul>\n"
                    inside_list = True
                parts = item.split(" ", 1)
                text = parts[1] if len(parts) > 1 else item
                html += f"  <li>{text}</li>\n"
            else:
                if inside_list:
                    html += "</ul>\n"
                    inside_list = False
                html += f"<p>{item}</p>\n"
        if inside_list:
            html += "</ul>\n"

        return html





    def split_mermaid_blocks(code: str):
        """Split mermaid code into separate blocks for rendering."""
        diagram_keywords = (
            "graph", "flowchart", "sequenceDiagram", "erDiagram",
            "classDiagram", "stateDiagram", "stateDiagram-v2", "pie"
        )
        blocks = []
        current = []
        for line in code.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(k) for k in diagram_keywords):
                if current:
                    blocks.append("\n".join(current))
                    current = []
            if stripped:
                current.append(line)
        if current:
            blocks.append("\n".join(current))
        return blocks

    # Extract and normalize fields
    title = report.get("TITLE", "Security Report")
    executive_summary = normalize_text_field(report.get("EXECUTIVE_SUMMARY", []))
    detailed_analysis = normalize_text_field(report.get("DETAILED_ANALYSIS", []))
    risk_assessment_list = normalize_text_field(report.get("RISK_ASSESSMENT", []))
    mitigation_list = normalize_text_field(report.get("MITIGATION", []))
    threat_model_code = report.get("THREAT_MODEL", "")

    # Process mermaid diagrams
    threat_blocks = split_mermaid_blocks(threat_model_code)
    threat_model_html = ""
    for block in threat_blocks:
        threat_model_html += f'<div class="mermaid">\n{block.strip()}\n</div>\n'

    # Render HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{ startOnLoad: true }});</script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f9f9f9; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; }}
        .section {{ background: #fff; border-radius: 8px; padding: 15px 20px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        .mermaid {{ background: #fff; border-radius: 8px; padding: 10px; margin-top: 10px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>

    <div class="section">
        <h2>Executive Summary</h2>
        {generate_list(executive_summary)}
    </div>

    <div class="section">
        <h2>Detailed Analysis</h2>
        {generate_list(detailed_analysis)}
    </div>

    <div class="section">
        <h2>Risk Assessment</h2>
        {generate_list(risk_assessment_list)}
    </div>

    <div class="section">
        <h2>Threat Model</h2>
        {threat_model_html if threat_model_html else "<p><b>No threat model diagrams available</b></p>"}
    </div>

    <div class="section">
        <h2>Mitigation</h2>
        {generate_list(mitigation_list)}
    </div>
</body>
</html>
"""
    return html