import re

def sanitize_cve_id(cve):
    clean_input = cve.strip().upper()
    pattern = r"^CVE-\d{4}-\d{4,6}$"
    
    if not re.match(pattern, cve):
        raise ValueError("Invalid CVE format. Expected CVE-YYYY-NNNN")
    return cve


def sanitize_llm(content: str) -> str:
    if not content:
        return ""

    # Remove markdown headers (#, ##, ### ...)
    content = re.sub(r'^\s*#{1,6}\s*', '', content, flags=re.MULTILINE)

    # Remove <think>...</think> or any similar tags
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE)

    # Remove bold/italic markers (**text**, *text*, __text__, _text_)
    content = re.sub(r'(\*\*|__)(.*?)\1', r'\2', content)
    content = re.sub(r'(\*|_)(.*?)\1', r'\2', content)

    # Remove inline code markers (`code`)
    content = re.sub(r'`([^`]*)`', r'\1', content)

    # Remove code fences like ```mermaid or ```html
    content = re.sub(r'```(?:mermaid|html)?\s*', '', content)
    content = re.sub(r'```', '', content)

    # Remove any remaining excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Strip leading/trailing whitespace
    content = content.strip()

    return content


def extract_cve_id(text: str) -> str | None:
    pattern = r"\bCVE-\d{4}-\d{4,7}\b"

    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        # Standardize to uppercase CVE form
        return match.group(0).upper()
    return None
