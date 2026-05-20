"""Fix mojibake in training.ipynb.

The special characters were stored as their raw UTF-8 byte sequences
interpreted as latin-1 codepoints. For example, the en-dash U+2013 has
UTF-8 bytes E2 80 93. Those bytes read as latin-1 give the string made of
codepoints 0xE2, 0x80, 0x93 which in a UTF-8 Python string is the three-char
sequence chr(0xe2)+chr(0x80)+chr(0x93). This script maps those back.
"""
from pathlib import Path

NB_PATH = Path(__file__).parent.parent / "notebooks" / "training.ipynb"

text = NB_PATH.read_text(encoding="utf-8")

# Keys are the mojibake strings (chr sequences), values are the correct chars.
# Using chr() so no special chars appear in this source file.
REPLACEMENTS = [
    (chr(0xe2)+chr(0x80)+chr(0x94), chr(0x2014)),  # em dash
    (chr(0xe2)+chr(0x80)+chr(0x93), chr(0x2013)),  # en dash
    (chr(0xe2)+chr(0x86)+chr(0x92), chr(0x2192)),  # right arrow
    (chr(0xe2)+chr(0x94)+chr(0x80), chr(0x2500)),  # box drawing light horiz
    (chr(0xc2)+chr(0xb7),           chr(0x00b7)),  # middle dot
    (chr(0xc2)+chr(0xa0),           " "),          # non-breaking space -> regular space
    (chr(0xc2),                     ""),            # stray Â with no follow byte
]

for bad, good in REPLACEMENTS:
    text = text.replace(bad, good)

NB_PATH.write_text(text, encoding="utf-8")

remaining = sorted(set(
    hex(ord(c)) for c in text
    if ord(c) > 127 and ord(c) not in (
        0x00b7,  # middle dot (intentional)
        0x2013,  # en dash (intentional)
        0x2014,  # em dash (intentional)
        0x2192,  # right arrow (intentional)
        0x2500,  # box drawing horiz (intentional)
        0x00b0,  # degree sign
        0x2019, 0x2018,  # curly quotes in prose
        0x201c, 0x201d,
    )
))
if remaining:
    print("Still-unusual codepoints:", remaining)
    import re
    for hex_cp in remaining[:5]:
        cp = int(hex_cp, 16)
        idx = text.find(chr(cp))
        print(f"  {hex_cp}: ...{repr(text[max(0,idx-30):idx+30])}...")
else:
    print("All mojibake fixed. Notebook is clean.")
