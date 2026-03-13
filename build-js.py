#!/usr/bin/env python3

"""
Build script to combine and minify JavaScript files
Scans static/js for *.js files (excluding *.min.js and chart files)
"""

import os
import sys
import subprocess
import re
from pathlib import Path

# Configuration
JS_DIR = Path("static/js")
RELEASE_DIR = Path("static/js/release")
OUTPUT_FILE = RELEASE_DIR / "app.min.js"
INDEX_HTML = Path("static/index.html")

# Files to exclude from bundling
EXCLUDE_PATTERNS = [
    r".*\.min\.js$",          # Already minified files
    r".*chart.*\.js$",         # Chart.js and plugins
    r".*/release/.*",          # Files in release directory
]

# Note: Preferred order is extracted from index.html.dev to maintain single source of truth
PREFERRED_ORDER = []  # Will be populated from index.html.dev if it exists


def should_exclude(filepath):
    """Check if file should be excluded from bundling"""
    filepath_str = str(filepath)
    for pattern in EXCLUDE_PATTERNS:
        if re.match(pattern, filepath_str, re.IGNORECASE):
            return True
    return False


def extract_script_order_from_html():
    """Extract JS file order from index.html.dev"""
    dev_html = Path("static/index.html.dev")
    
    if not dev_html.exists():
        print(f"❌ Error: {dev_html} not found")
        print(f"   This file is required as the single source of truth for script order.")
        print(f"   Please create it with individual <script> tags in dependency order.")
        sys.exit(1)
    
    content = dev_html.read_text()
    order = []
    
    # Find all script tags in the JavaScript modules section
    pattern = r'<script src="js/([^"]+\.js)(?:\?v=[^"]*)?"></script>'
    matches = re.findall(pattern, content)
    
    for match in matches:
        # Exclude chart files
        if 'chart' not in match.lower() and not match.endswith('.min.js'):
            order.append(match)
    
    if not order:
        print(f"❌ Error: No JavaScript files found in {dev_html}")
        print(f"   Expected <script src=\"js/*.js\"> tags in the file.")
        sys.exit(1)
    
    return order


def get_js_files():
    """Scan and return list of JS files to bundle"""
    if not JS_DIR.exists():
        print(f"❌ Error: {JS_DIR} directory not found")
        sys.exit(1)
    
    # Get preferred order from HTML
    preferred_order = extract_script_order_from_html()
    
    # Find all .js files
    all_files = []
    for js_file in JS_DIR.rglob("*.js"):
        if not should_exclude(js_file):
            all_files.append(js_file)
    
    # Sort files by preferred order
    ordered_files = []
    
    # Add files in preferred order first
    for preferred in preferred_order:
        target = JS_DIR / preferred
        if target in all_files:
            ordered_files.append(target)
            all_files.remove(target)
    
    # Add remaining files (sorted alphabetically)
    remaining_files = sorted(all_files)
    
    return ordered_files + remaining_files


def get_version(args):
    """Determine version from args or index.html"""
    if len(args) > 1:
        return args[1]
    
    # Try to extract from index.html
    if INDEX_HTML.exists():
        content = INDEX_HTML.read_text()
        match = re.search(r'js/release/app\.min\.js\?v=([0-9]+\.[0-9]+\.[0-9]+)', content)
        if match:
            return match.group(1)
    
    return "0.5.0"


def combine_files(js_files):
    """Combine all JS files into one"""
    combined = []
    
    print(f"📦 Combining {len(js_files)} JavaScript files...")
    
    for js_file in js_files:
        print(f"  ✓ Adding {js_file.relative_to(JS_DIR)}")
        content = js_file.read_text()
        combined.append(content)
    
    return "\n\n".join(combined)


def minify(content, output_file):
    """Minify JavaScript using terser"""
    print("⚡ Minifying with terser...")
    
    # Create temp file
    temp_file = RELEASE_DIR / "app.temp.js"
    temp_file.write_text(content)
    
    try:
        result = subprocess.run(
            ["terser", str(temp_file), "-o", str(output_file), "--compress", "--mangle", "--toplevel"],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Clean up temp file
        temp_file.unlink()
        
        # Get file size
        size_kb = output_file.stat().st_size / 1024
        print(f"✅ Build complete: {output_file}")
        print(f"   Size: {size_kb:.2f} KB")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during minification: {e.stderr}")
        if temp_file.exists():
            temp_file.unlink()
        return False
    except FileNotFoundError:
        print("❌ Error: terser not found. Please install it first:")
        print("   npm install -g terser")
        if temp_file.exists():
            temp_file.unlink()
        return False


def update_index_html(version):
    """Update index.html with new version"""
    print("📝 Updating index.html with version...")
    
    # Check if we're using dev/prod split
    dev_html = Path("static/index.html.dev")
    
    if dev_html.exists():
        # Copy dev to production and replace scripts
        print(f"   Using {dev_html} as source...")
        content = dev_html.read_text()
        
        # Replace the entire JavaScript modules section with minified version
        pattern = r'<!-- JavaScript modules -->.*?</body>'
        replacement = f'<!-- JavaScript modules -->\n    <script src="js/release/app.min.js?v={version}"></script>\n</body>'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        INDEX_HTML.write_text(new_content)
        print(f"✅ {INDEX_HTML} generated from {dev_html}")
    else:
        # Fallback: update existing index.html
        if not INDEX_HTML.exists():
            print(f"⚠ Warning: {INDEX_HTML} not found, skipping...")
            return
        
        # Create backup
        backup = INDEX_HTML.with_suffix(".html.bak")
        INDEX_HTML.replace(backup)
        content = backup.read_text()
        
        # Replace the script section
        pattern = r'<!-- JavaScript modules -->.*?<script src="js/main\.js\?v=[^"]+"></script>'
        replacement = f'<!-- JavaScript modules -->\n    <script src="js/release/app.min.js?v={version}"></script>'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        INDEX_HTML.write_text(new_content)
        print("✅ index.html updated successfully")


def main():
    """Main build process"""
    print("🔨 Building JavaScript bundle...")
    
    # Get version
    version = get_version(sys.argv)
    print(f"   Version: {version}")
    
    # Create release directory
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get JS files
    js_files = get_js_files()
    
    if not js_files:
        print("⚠ Warning: No JavaScript files found to bundle")
        sys.exit(1)
    
    # Combine files
    combined_content = combine_files(js_files)
    
    # Minify
    if not minify(combined_content, OUTPUT_FILE):
        sys.exit(1)
    
    # Update index.html
    update_index_html(version)
    
    print()
    print("🎉 Build process complete!")
    print()
    print("Usage examples:")
    print("  ./build-js.py          # Use current version from index.html")
    print("  ./build-js.py 0.6.0    # Specify new version")


if __name__ == "__main__":
    main()
