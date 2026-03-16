"""Configuration for the Command Center."""
import os
from pathlib import Path

class Config:
    # Flask
    SECRET_KEY = os.urandom(32)
    HOST = '127.0.0.1'  # localhost ONLY
    PORT = 5000
    DEBUG = False  # Never True in use

    # Case data directory — configurable
    CASE_DIR = os.environ.get(
        'CIPHERGY_CASE_DIR',
        '/Users/bopennington/LEGAL 2026 Pro Se/CAMPENNI_CASE'
    )

    # Ciphergy product directory
    PRODUCT_DIR = os.environ.get(
        'CIPHERGY_PRODUCT_DIR',
        '/Users/bopennington/LEGAL 2026 Pro Se/CIPHERGY'
    )

    # Templates directory (in product)
    TEMPLATES_DIR = os.path.join(PRODUCT_DIR, 'templates')

    # Mail config
    MAIL_PROVIDER = os.environ.get('CIPHERGY_MAIL_PROVIDER', 'lob')
    MAIL_API_KEY_FILE = os.path.join(PRODUCT_DIR, '.keys', 'mail_api.key')

    # Encryption
    ENCRYPTION_KEY_FILE = os.path.join(PRODUCT_DIR, '.keys', 'comm.key')

    # Security
    PROTECTED_DIRS = [
        '01_ACTIVE_FILINGS',
        '02_STANDBY_WEAPONS',
        '03_EVIDENCE',
        '04_CORRESPONDENCE',
        '05_BAR_COMPLAINTS',
        '06_SETTLEMENT',
        '07_STRATEGY',
        '08_DAMAGES',
        '09_COURT_FORMS',
        '10_DISCOVERY',
        '11_VENDOR_BALANCES',
        'THE_LAW',
        'Bo',
    ]
