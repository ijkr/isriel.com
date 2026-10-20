#!/usr/bin/env python3
"""
Post-process the StatiCrypt output into publishable files.

The served page IS the encrypted shell, so anything a crawler or a
link-preview bot must honour - robots, referrer policy - has to be injected
into the OUTER document. A robots meta inside the encrypted payload is
invisible to crawlers because it only exists after client-side decryption.

  build/*.html  ->  build/*.html  (robots + referrer meta injected, idempotent)
"""
import os, re, glob, sys

BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
INJECT = ('<meta name="robots" content="noindex,nofollow,noarchive,noimageindex" />\n'
          '        <meta name="referrer" content="no-referrer" />\n'
          '        <meta name="googlebot" content="noindex,nofollow" />\n')


def main():
    n = 0
    for f in sorted(glob.glob(os.path.join(BUILD, "*.html"))):
        s = open(f, encoding="utf-8").read()
        if 'name="robots"' in s:
            print(f"  skip (already hardened) {os.path.basename(f)}")
            continue
        s2, k = re.subn(r"(<title>[^<]*</title>\n)", r"\1        " + INJECT, s, count=1)
        if k != 1:
            print(f"  FAILED to inject into {os.path.basename(f)}", file=sys.stderr)
            return 1
        open(f, "w", encoding="utf-8").write(s2)
        print(f"  hardened {os.path.basename(f)}")
        n += 1
    print(f"{n} files hardened")
    return 0


if __name__ == "__main__":
    sys.exit(main())
