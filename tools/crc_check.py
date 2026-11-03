#!/usr/bin/env python3
"""Check stock phone modules against a new kernel's vmlinux.symvers.

For every imported symbol in each module's __versions section:
  - exported by the new vmlinux  -> CRC must match
  - exported by another stock module -> fine (both stock)
  - neither -> missing export
Usage: crc_check.py vmlinux.symvers module_dir...
"""
import os, struct, sys
from collections import defaultdict

SIG = b'~Module signature appended~\n'

def sections(data):
    shoff, = struct.unpack_from('<Q', data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', data, 0x3A)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + i * shentsize) for i in range(shnum)]
    stro = hdrs[shstrndx][4]
    out = {}
    for h in hdrs:
        name = data[stro + h[0]:data.index(b'\0', stro + h[0])].decode()
        out[name] = data[h[4]:h[4] + h[5]]
    return out

def versions(sec):
    # struct modversion_info { unsigned long crc; char name[56]; }
    for i in range(0, len(sec), 64):
        crc, = struct.unpack_from('<Q', sec, i)
        yield sec[i + 8:i + 64].split(b'\0')[0].decode(), crc & 0xffffffff

def modinfo(sec):
    return dict(kv.split('=', 1) for kv in sec.decode(errors='replace').split('\0') if '=' in kv)

def load_symvers(path):
    return {f[1]: int(f[0], 16) for f in (l.split('\t') for l in open(path)) if len(f) >= 2}

def main(symvers, dirs):
    kern = load_symvers(symvers)
    mods = {}
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith('.ko'):
                    p = os.path.join(root, f)
                    mods[os.path.relpath(p)] = p
    exported_by_mods = set()
    parsed = {}
    for name, p in mods.items():
        data = open(p, 'rb').read()
        s = sections(data)
        parsed[name] = (s, data.endswith(SIG))
        exported_by_mods.update(x.decode() for x in s.get('__ksymtab_strings', b'').split(b'\0') if x)

    bad = defaultdict(list); missing = defaultdict(list)
    checked = 0; vermagic = defaultdict(int); scm = defaultdict(int); signed = 0
    for name, (s, is_signed) in sorted(parsed.items()):
        mi = modinfo(s.get('.modinfo', b''))
        vermagic[mi.get('vermagic', '?')] += 1
        scm[mi.get('scmversion', '-')] += 1
        signed += is_signed
        for sym, crc in versions(s.get('__versions', b'')):
            checked += 1
            if sym in kern:
                if kern[sym] != crc:
                    bad[name].append(f'{sym} module=0x{crc:08x} kernel=0x{kern[sym]:08x}')
            elif sym not in exported_by_mods:
                missing[name].append(sym)

    print(f'modules: {len(parsed)}  signed: {signed}  imports checked: {checked}  kernel exports: {len(kern)}')
    print('vermagic:', dict(vermagic))
    print('scmversion:', dict(scm))
    print(f'CRC mismatches: {sum(map(len, bad.values()))} in {len(bad)} modules')
    for m, l in bad.items():
        print(f'  {m}:'); [print('    ' + x) for x in l]
    print(f'missing exports: {sum(map(len, missing.values()))} in {len(missing)} modules')
    for m, l in missing.items():
        print(f'  {m}: {", ".join(l)}')
    return 1 if bad or missing else 0

def selftest():
    sec = struct.pack('<Q', 0x1234abcd) + b'printk'.ljust(56, b'\0')
    assert list(versions(sec)) == [('printk', 0x1234abcd)]
    assert modinfo(b'vermagic=6.1 SMP\0license=GPL\0') == {'vermagic': '6.1 SMP', 'license': 'GPL'}
    print('ok')

if __name__ == '__main__':
    if len(sys.argv) < 3 and sys.argv[1:] != ['--selftest']:
        sys.exit(__doc__)
    if sys.argv[1:] == ['--selftest']:
        selftest()
    else:
        sys.exit(main(sys.argv[1], sys.argv[2:]))
