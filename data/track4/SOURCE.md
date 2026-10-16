# Track 4 source snapshot

- Problem statement: https://datathon-xi.vercel.app/problem-statements.html#track-4
- Original archive: https://datathon-xi.vercel.app/datasets/04_business_money_leak.zip
- Snapshot downloaded during this project on 16 October 2026.
- Original directory: `04_business_money_leak/`; five CSV files and the supplied `README.txt` are preserved.
- The CSV bytes were checked against the original downloaded archive after the model work; all five match. `reports/evaluation.json` records SHA-256 checksums of each source CSV and each generated prediction artifact.
- The challenge describes these records as synthetic educational data. No real business data is implied. The supplied README warns that independent cost/price generation can create unrealistic margins.
- No source cells were corrected, removed, or overwritten. Modeling exclusions, same-day stock collapsing, and consistency warnings are performed on derived in-memory tables and documented in the audit and model cards.
- The analysis covers the five business files for Track 4. The health, campus-space, and smart-city tracks are separate challenges and are not silently combined with retail records.

The live problem page was unavailable during the final refresh attempt; implementation alignment used the original problem-page snapshot and downloaded archive from the same project session. Source checksums make the evaluated snapshot explicit rather than claiming an unverified latest version.
