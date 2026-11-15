# Integrated QA output workspace

No QA report is pre-generated. Run `python scripts/terrascan_qa.py project --output data/qa/project-audit.json`. Output files are immutable; choose a new filename for each audit. The audit is structural/static only and does not establish scientific validity or operational readiness.

For file integrity verification, provide a separate manifest of paths and SHA-256 hashes to the `integrity` subcommand.
