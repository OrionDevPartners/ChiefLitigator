#!/usr/bin/env python3
"""
Ciphergy Frontend Build Script
Minifies and obfuscates JavaScript files for production deployment.

Usage:
    python3 scripts/build_frontend.py [dev|prod]

    dev  — base.html references app.js (readable source)
    prod — base.html references app.min.js (obfuscated)
"""

import re
import string
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
COMMAND_CENTER = PROJECT_DIR / "ciphergy" / "command_center"
STATIC_JS = COMMAND_CENTER / "static" / "js"
TEMPLATES = COMMAND_CENTER / "templates"
BASE_HTML = TEMPLATES / "base.html"

JS_FILES = ["app.js", "assistant.js", "mail_compose.js"]

# ---------------------------------------------------------------------------
# Minifier — remove comments and collapse whitespace
# ---------------------------------------------------------------------------


def strip_comments(source: str) -> str:
    """Remove single-line and multi-line JS comments, preserving strings."""
    result = []
    i = 0
    length = len(source)
    while i < length:
        # String literals — pass through unchanged
        if source[i] in ('"', "'", "`"):
            quote = source[i]
            result.append(source[i])
            i += 1
            while i < length and source[i] != quote:
                if source[i] == "\\" and i + 1 < length:
                    result.append(source[i])
                    i += 1
                result.append(source[i])
                i += 1
            if i < length:
                result.append(source[i])
                i += 1
        # Multi-line comment
        elif source[i] == "/" and i + 1 < length and source[i + 1] == "*":
            i += 2
            while i < length - 1 and not (source[i] == "*" and source[i + 1] == "/"):
                i += 1
            i += 2  # skip */
        # Single-line comment
        elif source[i] == "/" and i + 1 < length and source[i + 1] == "/":
            i += 2
            while i < length and source[i] != "\n":
                i += 1
        else:
            result.append(source[i])
            i += 1
    return "".join(result)


def collapse_whitespace(source: str) -> str:
    """Collapse multiple whitespace/newlines into minimal spacing."""
    # Replace multiple spaces/tabs with single space
    source = re.sub(r"[ \t]+", " ", source)
    # Remove spaces around operators/punctuation (careful with keywords)
    source = re.sub(r"\s*([{}\[\]();,=+\-*/<>!&|?:~^%])\s*", r"\1", source)
    # Remove blank lines
    source = re.sub(r"\n\s*\n", "\n", source)
    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in source.split("\n") if line.strip()]
    return "\n".join(lines)


def minify(source: str) -> str:
    """Full minification pipeline."""
    source = strip_comments(source)
    source = collapse_whitespace(source)
    return source


# ---------------------------------------------------------------------------
# Obfuscator — rename local variables, encode strings
# ---------------------------------------------------------------------------

# Functions called from HTML onclick attributes — must NOT be renamed
PRESERVED_NAMES = {
    "toggleSidebar",
    "toggleDrawer",
    "switchTab",
    "toggleCollapsible",
    "showTemplateInfo",
    "generatePrompt",
    "copyPrompt",
    "runDraftCheck",
    "showToast",
    # Built-in globals
    "document",
    "window",
    "fetch",
    "console",
    "alert",
    "setTimeout",
    "setInterval",
    "clearInterval",
    "clearTimeout",
    "parseInt",
    "parseFloat",
    "isNaN",
    "JSON",
    "Array",
    "Object",
    "String",
    "Date",
    "Math",
    "FormData",
    "location",
    "sessionStorage",
    "localStorage",
    "navigator",
    "encodeURIComponent",
    "decodeURIComponent",
    "Boolean",
    "Number",
    "RegExp",
    "Error",
    "Promise",
    "undefined",
    "null",
    "true",
    "false",
    "this",
    "arguments",
    "NaN",
    "Infinity",
}


def generate_var_names():
    """Generate short variable names: a, b, ..., z, aa, ab, ..."""
    chars = string.ascii_lowercase
    for c in chars:
        yield "_" + c
    for c1 in chars:
        for c2 in chars:
            yield "_" + c1 + c2


def find_local_vars(source: str) -> list:
    """Find var/let/const declarations to rename."""
    # Match: var x, let x, const x (but not in strings)
    pattern = r"\b(?:var|let|const)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)"
    found = re.findall(pattern, source)
    # Also find function parameter names in non-global functions
    func_params = re.findall(r"function\s*\w*\s*\(([^)]*)\)", source)
    for params in func_params:
        for p in params.split(","):
            p = p.strip()
            if p and p not in PRESERVED_NAMES:
                found.append(p)
    # Deduplicate, preserving order
    seen = set()
    unique = []
    for name in found:
        if name not in seen and name not in PRESERVED_NAMES and len(name) > 2:
            seen.add(name)
            unique.append(name)
    return unique


def encode_string_literal(s: str) -> str:
    """Encode a string as String.fromCharCode(...) for obfuscation."""
    if len(s) > 60 or len(s) < 4:
        return None  # Skip very long or very short strings
    codes = ",".join(str(ord(c)) for c in s)
    return f"String.fromCharCode({codes})"


def obfuscate_strings(source: str) -> str:
    """Replace some string literals with charCode encoding."""

    def replace_string(match):
        quote = match.group(0)[0]
        content = match.group(0)[1:-1]
        # Skip strings with escape sequences, template expressions, HTML
        if "\\" in content or "<" in content or ">" in content:
            return match.group(0)
        if len(content) < 4 or len(content) > 50:
            return match.group(0)
        # Only encode ~40% of eligible strings (deterministic by hash)
        if hash(content) % 5 < 3:
            return match.group(0)
        encoded = encode_string_literal(content)
        if encoded:
            return encoded
        return match.group(0)

    # Match single and double quoted strings (not in comments — already stripped)
    result = re.sub(r"'[^'\\]*'|\"[^\"\\]*\"", replace_string, source)
    return result


def rename_variables(source: str, var_list: list) -> str:
    """Rename local variables to short names."""
    gen = generate_var_names()
    renames = {}
    for var in var_list:
        short = next(gen)
        renames[var] = short

    for original, short in renames.items():
        # Use word boundary replacement to avoid partial matches
        source = re.sub(r"\b" + re.escape(original) + r"\b", short, source)

    return source


def obfuscate(source: str) -> str:
    """Full obfuscation pipeline."""
    minified = minify(source)
    local_vars = find_local_vars(minified)
    result = rename_variables(minified, local_vars)
    result = obfuscate_strings(result)
    # Wrap in IIFE
    result = "// Ciphergy v1.0 \u2014 Compiled\n;(function(){" + result + "})();"
    return result


# ---------------------------------------------------------------------------
# HTML updater — swap app.js <-> app.min.js in base.html
# ---------------------------------------------------------------------------


def update_base_html(mode: str):
    """Switch base.html between dev (app.js) and prod (app.min.js) references."""
    html = BASE_HTML.read_text()

    if mode == "prod":
        # For each JS file, replace .js with .min.js
        for js_file in JS_FILES:
            min_file = js_file.replace(".js", ".min.js")
            html = (
                html.replace(f"filename='{js_file}'", f"filename='{min_file}'")
                .replace(f'filename="{js_file}"', f'filename="{min_file}"')
                .replace(f"filename='js/{js_file}'", f"filename='js/{min_file}'")
                .replace(f'filename="js/{js_file}"', f'filename="js/{min_file}"')
            )
    else:
        # Reverse: .min.js -> .js
        for js_file in JS_FILES:
            min_file = js_file.replace(".js", ".min.js")
            html = (
                html.replace(f"filename='{min_file}'", f"filename='{js_file}'")
                .replace(f'filename="{min_file}"', f'filename="{js_file}"')
                .replace(f"filename='js/{min_file}'", f"filename='js/{js_file}'")
                .replace(f'filename="js/{min_file}"', f'filename="js/{js_file}"')
            )

    BASE_HTML.write_text(html)

    # Also update assistant.html and mail_compose.html
    for template_name in ["assistant.html", "mail_compose.html"]:
        template_path = TEMPLATES / template_name
        if template_path.exists():
            tmpl = template_path.read_text()
            if mode == "prod":
                for js_file in JS_FILES:
                    min_file = js_file.replace(".js", ".min.js")
                    tmpl = tmpl.replace(f"filename='js/{js_file}'", f"filename='js/{min_file}'").replace(
                        f'filename="js/{js_file}"', f'filename="js/{min_file}"'
                    )
            else:
                for js_file in JS_FILES:
                    min_file = js_file.replace(".js", ".min.js")
                    tmpl = tmpl.replace(f"filename='js/{min_file}'", f"filename='js/{js_file}'").replace(
                        f'filename="js/{min_file}"', f'filename="js/{js_file}"'
                    )
            template_path.write_text(tmpl)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "prod"

    if mode not in ("dev", "prod"):
        print(f"Usage: {sys.argv[0]} [dev|prod]")
        print("  dev  — use readable app.js")
        print("  prod — use obfuscated app.min.js")
        sys.exit(1)

    print(f"Ciphergy Frontend Build — mode: {mode}")
    print(f"  JS source dir: {STATIC_JS}")
    print()

    if mode == "prod":
        for js_file in JS_FILES:
            source_path = STATIC_JS / js_file
            min_path = STATIC_JS / js_file.replace(".js", ".min.js")

            if not source_path.exists():
                print(f"  SKIP {js_file} — not found")
                continue

            source = source_path.read_text()
            original_size = len(source)

            result = obfuscate(source)
            min_path.write_text(result)

            new_size = len(result)
            ratio = (1 - new_size / original_size) * 100 if original_size > 0 else 0
            print(
                f"  {js_file}: {original_size:,} bytes -> {js_file.replace('.js', '.min.js')}: {new_size:,} bytes ({ratio:.0f}% reduction)"
            )

        update_base_html("prod")
        print()
        print("  Templates updated to reference .min.js files")
        print("  Production build complete.")

    else:
        update_base_html("dev")
        print("  Templates updated to reference source .js files")
        print("  Development mode active.")


if __name__ == "__main__":
    main()
