#!/usr/bin/env python3
"""Verifier's own minimal PDF text scraper (no third-party deps).
Walks every 'stream ... endstream', tries zlib inflate (falls back to raw bytes),
and for content streams collects string operands of Tj / ' / " / TJ operators in order.
Strings inside TJ arrays are joined; a large negative kern (< -200) is rendered as a space.
Also emits hex strings. Output is lower-fidelity than pdftotext but grep-able.
Usage: python3 pdftext.py file.pdf > file.txt
"""
import re, sys, zlib

data = open(sys.argv[1], 'rb').read()
out = []

def unescape(s):
    # PDF literal string escapes
    s = re.sub(rb'\\([0-7]{1,3})', lambda m: bytes([int(m.group(1), 8) & 0xFF]), s)
    for a, b in ((rb'\\n', b'\n'), (rb'\\r', b''), (rb'\\t', b' '), (rb'\\(', b'('), (rb'\\)', b')'), (rb'\\\\', b'\\')):
        s = s.replace(a, b)
    return s

tok = re.compile(rb'\((?:[^()\\]|\\.)*\)|<[0-9A-Fa-f\s]+>|\[|\]|-?\d+\.?\d*|[A-Za-z\'"*]+', re.S)

for m in re.finditer(rb'stream\r?\n', data):
    st = m.end()
    en = data.find(b'endstream', st)
    if en < 0:
        continue
    raw = data[st:en]
    dec = None
    try:
        dec = zlib.decompress(raw)
    except Exception:
        try:
            dec = zlib.decompressobj().decompress(raw)
        except Exception:
            dec = raw
    if b'Tj' not in dec and b'TJ' not in dec and b"'" not in dec:
        continue
    in_arr = False
    pending = []
    for t in tok.finditer(dec):
        s = t.group(0)
        if s == b'[':
            in_arr = True; pending = []
        elif s == b']':
            in_arr = False
        elif s.startswith(b'('):
            txt = unescape(s[1:-1])
            if in_arr: pending.append(txt)
            else: pending = [txt]
        elif s.startswith(b'<'):
            try:
                txt = bytes.fromhex(re.sub(rb'\s', b'', s[1:-1]).decode())
            except Exception:
                txt = b''
            if in_arr: pending.append(txt)
            else: pending = [txt]
        elif in_arr and re.match(rb'-?\d', s):
            try:
                if float(s) < -200: pending.append(b' ')
            except Exception: pass
        elif s in (b'Tj', b'TJ', b"'", b'"'):
            out.append(b''.join(pending)); pending = []
            if s in (b"'", b'"'): out.append(b'\n')
        elif s in (b'Td', b'TD', b'T*', b'ET'):
            out.append(b'\n')
sys.stdout.write(b''.join(out).decode('latin1'))
