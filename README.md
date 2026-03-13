# Broken Link Checker

---

Broken links make public‑facing websites harder to navigate, especially when pages change or old references disappear. This tool automates the job of checking whether those links still work, moving through pages on its own and recording every issue it finds.

Calling it **high‑performance** and **asynchronous** simply means it can prepare multiple checks at once instead of waiting for each page to finish loading before starting the next. That makes large audits faster and more reliable. 

At the same time, it treats public websites with care: the default concurrency is set to **1**, so it checks links one at a time by default. This limit can be raised in `config.py` when working with systems that can safely handle more traffic.

The result is a practical, respectful way to keep online resource directories accurate and easy for the public to use.

---

## Directory Structure

```text
broken-link-checker/
├── data/
│   ├── targets.json      # Hierarchical crawl targets
│   └── reports/          # Generated .csv audit logs
├── src/
│   ├── config.py         # BASE_DIR and global constants
│   ├── models.py         # Dataclasses (ValidationResult, AuditResult)
│   ├── crawler.py        # Playwright crawler (The Scout)
│   ├── auditor.py        # HTTPX Async validator (The Inspector)
│   └── manager.py        # Orchestration & Reporting (The Director)
├── main.py               # Entry Point
└── tests/                # Pytest suite

```

## Configure Targets

Edit `data/targets.json` to define your crawling depth and CSS selectors:

For example, the snippet means: Go to `base_url`, 
dive in each page that matches the selector of `follow`, 
and validate all hyperlinks that match the selector of `validate`

```json
[
  {
    "base_url": "https://bpl.bc.ca/people-help/information-community-resources",
    "levels": [
        {
            "selector": ".link-menu-tile-half a",
            "action": "follow"
        },
        {
            "selector": ".accordion a",
            "action": "validate"
        }
        ]
  },
]

```


## Reporting

The Manager generates reports in `data/reports/` using the following logic:

* **Priority Sorting**: Broken links and Soft 404s are floated to the top.
* **Context Preservation**: Maps unique audit "verdicts" back to every parent page occurrence.
* **Timestamped**: Filenames follow the `audit_YYYYMMDD_HHMM.csv` format.
