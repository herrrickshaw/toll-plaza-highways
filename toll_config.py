"""Shared configuration for the toll-plaza scripts.

The scripts historically read and wrote under one user's home directory.
Those locations are kept as the defaults (so existing invocations behave
identically) but live here in one place instead of being repeated inline.
"""

from __future__ import annotations

from pathlib import Path

HOME_DIR = '/Users/umashankar'
DOWNLOADS_DIR = Path(HOME_DIR) / 'Downloads'

PLAZAS_CSV = DOWNLOADS_DIR / 'toll_plazas_cleaned.csv'
SAMPLE_PAYMENTS_CSV = DOWNLOADS_DIR / 'sample_payment_data.csv'

SOURCE_PDFS = [
    DOWNLOADS_DIR / 'NH-Fee-Plazas-1.pdf',
    DOWNLOADS_DIR / 'NH-Toll-Plaza-.pdf',
    DOWNLOADS_DIR / 'NHAI-toll-list.pdf',
]

# Rupee unit conversions used in reports.
LAKH = 100_000
CRORE = 10_000_000
