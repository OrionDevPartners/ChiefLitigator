#!/usr/bin/env python3
"""
CIPHERGY CRYPTO — AES-256-GCM Encryption Layer
Encrypts all inter-agent communications before they touch any external service.

Architecture:
    - AES-256-GCM (authenticated encryption — confidentiality + integrity)
    - 96-bit random nonce per message (never reused)
    - 256-bit key generated locally, stored locally, never transmitted
    - Output format: base64(nonce + ciphertext + tag) — single string safe for Asana
    - Prefix: "🔐CIPHERGY:" identifies encrypted messages

Usage:
    python3 scripts/crypto.py keygen                    — Generate a new AES-256 key
    python3 scripts/crypto.py encrypt "plaintext"       — Encrypt a string
    python3 scripts/crypto.py decrypt "ciphertext"      — Decrypt a string
    python3 scripts/crypto.py test                      — Run self-test

Programmatic:
    from crypto import CiphergyVault
    vault = CiphergyVault()          # auto-loads key
    encrypted = vault.encrypt("sensitive message")
    decrypted = vault.decrypt(encrypted)
"""

import os
import sys
import base64
import hashlib
import secrets
from pathlib import Path

# ================================================================
# CONFIG
# ================================================================

BASE = Path(__file__).resolve().parent.parent
KEY_DIR = BASE / ".keys"
KEY_FILE = KEY_DIR / "comm.key"
ENCRYPTED_PREFIX = "🔐CIPHERGY:"

# ================================================================
# AES-256-GCM IMPLEMENTATION
# ================================================================

class CiphergyVault:
    """AES-256-GCM encryption/decryption for inter-agent communications."""

    def __init__(self, key_path=None):
        """Initialize vault with key from file."""
        self.key_path = Path(key_path) if key_path else KEY_FILE
        self._key = None

    @property
    def key(self):
        """Lazy-load key from file."""
        if self._key is None:
            if not self.key_path.exists():
                raise FileNotFoundError(
                    f"No encryption key found at {self.key_path}. "
                    f"Run: python3 scripts/crypto.py keygen"
                )
            with open(self.key_path, "rb") as f:
                self._key = f.read()
            if len(self._key) != 32:
                raise ValueError(
                    f"Invalid key length: {len(self._key)} bytes (expected 32). "
                    f"Regenerate with: python3 scripts/crypto.py keygen"
                )
        return self._key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext with AES-256-GCM.

        Returns: base64 string prefixed with ENCRYPTED_PREFIX
        Format: prefix + base64(nonce[12] + ciphertext[variable] + tag[16])
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aesgcm = AESGCM(self.key)
        nonce = secrets.token_bytes(12)  # 96-bit nonce, cryptographically random
        plaintext_bytes = plaintext.encode("utf-8")

        # Encrypt — AESGCM appends the 16-byte auth tag to ciphertext
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)

        # Pack: nonce + ciphertext (includes tag)
        packed = nonce + ciphertext

        # Encode to base64 string (safe for Asana text fields)
        encoded = base64.b64encode(packed).decode("ascii")

        return f"{ENCRYPTED_PREFIX}{encoded}"

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted message.

        Input: string with ENCRYPTED_PREFIX + base64 payload
        Returns: decrypted plaintext string
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if not encrypted.startswith(ENCRYPTED_PREFIX):
            raise ValueError("Message is not encrypted (missing prefix)")

        # Strip prefix and decode base64
        encoded = encrypted[len(ENCRYPTED_PREFIX):]
        packed = base64.b64decode(encoded)

        # Unpack: nonce (12 bytes) + ciphertext+tag (rest)
        if len(packed) < 28:  # 12 nonce + 16 tag minimum
            raise ValueError("Encrypted message too short")

        nonce = packed[:12]
        ciphertext = packed[12:]

        # Decrypt and verify
        aesgcm = AESGCM(self.key)
        try:
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            raise ValueError(
                "Decryption failed — wrong key, corrupted message, or tampered data"
            )

        return plaintext_bytes.decode("utf-8")

    def is_encrypted(self, message: str) -> bool:
        """Check if a message is encrypted."""
        return message.startswith(ENCRYPTED_PREFIX)

# ================================================================
# KEY MANAGEMENT
# ================================================================

def generate_key(key_path=None):
    """Generate a new AES-256 key and save to file."""
    key_path = Path(key_path) if key_path else KEY_FILE

    # Create .keys directory with restricted permissions
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate 256-bit (32 byte) key
    key = secrets.token_bytes(32)

    # Save with restricted permissions (owner read/write only)
    with open(key_path, "wb") as f:
        f.write(key)
    os.chmod(key_path, 0o600)

    # Also create/update .gitignore in .keys/
    gitignore = key_path.parent / ".gitignore"
    with open(gitignore, "w") as f:
        f.write("# NEVER commit encryption keys\n*\n!.gitignore\n")

    # Compute key fingerprint (first 8 chars of SHA-256 hash) for identification
    fingerprint = hashlib.sha256(key).hexdigest()[:8]

    return key, fingerprint

def get_key_fingerprint(key_path=None):
    """Get the fingerprint of the current key."""
    key_path = Path(key_path) if key_path else KEY_FILE
    if not key_path.exists():
        return None
    with open(key_path, "rb") as f:
        key = f.read()
    return hashlib.sha256(key).hexdigest()[:8]

# ================================================================
# CLI
# ================================================================

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def cmd_keygen():
    """Generate a new AES-256 key."""
    if KEY_FILE.exists():
        fingerprint = get_key_fingerprint()
        print(f"{YELLOW}[WARN]{RESET} Key already exists (fingerprint: {fingerprint})")
        print(f"  Overwriting will make all previously encrypted messages unreadable.")
        print(f"  To proceed, delete {KEY_FILE} first.")
        return

    key, fingerprint = generate_key()
    print(f"{GREEN}[KEYGEN]{RESET} AES-256 key generated")
    print(f"  Location: {KEY_FILE}")
    print(f"  Fingerprint: {fingerprint}")
    print(f"  Permissions: 600 (owner read/write only)")
    print(f"")
    print(f"  {BOLD}IMPORTANT:{RESET}")
    print(f"  - This key NEVER leaves this machine")
    print(f"  - Share the fingerprint ({fingerprint}) with the other agent to confirm key match")
    print(f"  - Copy the key file to the other machine via secure channel (USB, AirDrop, encrypted transfer)")
    print(f"  - Both agents must have the SAME key file to communicate")
    print(f"  - The .keys/ directory is gitignored — it will never be committed")

def cmd_encrypt(plaintext):
    """Encrypt a message."""
    vault = CiphergyVault()
    encrypted = vault.encrypt(plaintext)
    print(encrypted)

def cmd_decrypt(ciphertext):
    """Decrypt a message."""
    vault = CiphergyVault()
    try:
        decrypted = vault.decrypt(ciphertext)
        print(decrypted)
    except ValueError as e:
        print(f"{RED}[ERROR]{RESET} {e}", file=sys.stderr)
        sys.exit(1)

def cmd_test():
    """Run encryption self-test."""
    print(f"\n{BOLD}CIPHERGY CRYPTO — SELF TEST{RESET}")
    print(f"{'─'*50}")

    # Generate temp key for testing
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
        test_key_path = f.name

    try:
        key, fingerprint = generate_key(test_key_path)
        vault = CiphergyVault(test_key_path)

        # Test 1: Basic encrypt/decrypt
        msg = "This is a test message with special chars: section 123.456 — $100,000.00 — user@example.com"
        encrypted = vault.encrypt(msg)
        decrypted = vault.decrypt(encrypted)
        assert decrypted == msg, f"Mismatch: {decrypted!r} != {msg!r}"
        print(f"  {GREEN}PASS{RESET} Basic encrypt/decrypt")

        # Test 2: Encrypted message has prefix
        assert encrypted.startswith(ENCRYPTED_PREFIX), "Missing prefix"
        print(f"  {GREEN}PASS{RESET} Encrypted prefix present")

        # Test 3: Different encryptions produce different ciphertext (random nonce)
        encrypted2 = vault.encrypt(msg)
        assert encrypted != encrypted2, "Same ciphertext — nonce reuse!"
        print(f"  {GREEN}PASS{RESET} Random nonce — no ciphertext reuse")

        # Test 4: Tampered message fails
        tampered = encrypted[:-5] + "XXXXX"
        try:
            vault.decrypt(tampered)
            assert False, "Should have failed on tampered message"
        except ValueError:
            pass
        print(f"  {GREEN}PASS{RESET} Tampered message rejected (authentication)")

        # Test 5: Wrong key fails
        key2, _ = generate_key(test_key_path + ".2")
        vault2 = CiphergyVault(test_key_path + ".2")
        try:
            vault2.decrypt(encrypted)
            assert False, "Should have failed with wrong key"
        except ValueError:
            pass
        os.unlink(test_key_path + ".2")
        print(f"  {GREEN}PASS{RESET} Wrong key rejected")

        # Test 6: is_encrypted detection
        assert vault.is_encrypted(encrypted), "Should detect encrypted"
        assert not vault.is_encrypted("plain text"), "Should detect plaintext"
        print(f"  {GREEN}PASS{RESET} Encrypted message detection")

        # Test 7: Empty message
        enc_empty = vault.encrypt("")
        dec_empty = vault.decrypt(enc_empty)
        assert dec_empty == "", "Empty message failed"
        print(f"  {GREEN}PASS{RESET} Empty message round-trip")

        # Test 8: Large message (simulate full comm)
        large_msg = "X" * 50000  # 50KB — larger than any comm we've sent
        enc_large = vault.encrypt(large_msg)
        dec_large = vault.decrypt(enc_large)
        assert dec_large == large_msg, "Large message failed"
        print(f"  {GREEN}PASS{RESET} Large message (50KB) round-trip")

        # Test 9: Unicode / emoji
        unicode_msg = "🔐 Ciphergy — section 123.456 — Party A v. Party B — $1,000,000.00"
        enc_uni = vault.encrypt(unicode_msg)
        dec_uni = vault.decrypt(enc_uni)
        assert dec_uni == unicode_msg, "Unicode failed"
        print(f"  {GREEN}PASS{RESET} Unicode/emoji round-trip")

        print(f"\n  {GREEN}{BOLD}ALL 9 TESTS PASSED{RESET}")
        print(f"  Key fingerprint: {fingerprint}")
        print(f"  Encrypted sample length: {len(encrypted)} chars (from {len(msg)} char input)")

    finally:
        os.unlink(test_key_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "keygen":
        cmd_keygen()
    elif cmd == "encrypt" and len(sys.argv) > 2:
        cmd_encrypt(" ".join(sys.argv[2:]))
    elif cmd == "decrypt" and len(sys.argv) > 2:
        cmd_decrypt(" ".join(sys.argv[2:]))
    elif cmd == "test":
        cmd_test()
    else:
        print(__doc__)
