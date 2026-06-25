"""One-off script: generate MEP / Electrical / Lost Time toolbox talk PDF."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Force local ReportLab generation (skip backend proxy).
os.environ.pop("SAPIENTIA_API_URL", None)

from utils.report_generator import generate_toolbox_talk_pdf
from utils.toolbox_talk import generate_toolbox_talk

OUTPUT = os.path.join(ROOT, "sample_data", "toolbox_talk_mep_electrical.pdf")


def main() -> str:
    talk = generate_toolbox_talk("MEP", "Electrical", "Lost Time")
    pdf_bytes = generate_toolbox_talk_pdf(talk)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "wb") as f:
        f.write(pdf_bytes)
    print(f"Wrote {len(pdf_bytes):,} bytes -> {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    main()
