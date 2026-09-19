#!/usr/bin/env python3
"""Crude, dependency-free PDF text extractor used to read primary sources
(no pypdf/pdftotext in this environment). Inflates FlateDecode streams and
collects the string operands of Tj/TJ operators. Word spacing is lost, but the
text is searchable. Usage: python3 extract_pdf_text.py file.pdf > file.txt
Used on:
  https://arxiv.org/pdf/math/9501233   (Gale-Propp-Sutherland-Troubetzkoy 1995)
  https://arxiv.org/pdf/nlin/0306022   (Gajardo-Moreira-Goles 2002, arXiv v2)
  https://gwern.net/doc/cs/cellular-automaton/1986-langton.pdf (Langton 1986, scan with OCR layer)
"""
import re, sys, zlib
d = open(sys.argv[1], 'rb').read()
parts = []
for m in re.finditer(rb'stream\r?\n', d):
    st = m.end(); en = d.find(b'endstream', st); raw = d[st:en]
    try:
        dec = zlib.decompress(raw)
    except Exception:
        try: dec = zlib.decompressobj().decompress(raw)
        except Exception: continue
    if b'Tj' not in dec and b'TJ' not in dec: continue
    parts += re.findall(rb'\((.*?)(?<!\\)\)', dec)
    for h in re.findall(rb'<([0-9A-Fa-f]+)>\s*Tj', dec):
        try: parts.append(bytes.fromhex(h.decode()))
        except Exception: pass
s = b''.join(parts).decode('latin1').replace('\\(', '(').replace('\\)', ')')
s = re.sub(r'\\\)-?[\d.]+\(', '"', s)
sys.stdout.write(s)
