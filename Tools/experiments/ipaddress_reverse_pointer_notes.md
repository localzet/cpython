# IPv6 reverse-pointer investigation

Issue: https://github.com/python/cpython/issues/91601

Related older discussions:
- https://github.com/python/cpython/issues/74713
- https://github.com/python/cpython/issues/125641

Reproduce with:
    python Tools/experiments/ipaddress_reverse_pointer_probe.py

Observed on Python 3.13.5: IPv6Interface and IPv6Network produce
reverse_pointer strings containing slash characters inherited from
the exploded display representation.

Open design decision:
1. Keep a string and return the host/network-address full reverse pointer.
2. Return an IPv6 prefix DNS zone for nibble-aligned networks; unaligned
   prefixes cannot be represented as one ordinary nibble-aligned zone.
3. Introduce explicit conversion or reject networks; this changes API
   behavior and may break consumers.

The old discussion and three earlier linked PRs must be reviewed before
claiming a backward-compatible fix. This experiment is a reproducer,
not a proposed CPython behavior change or new upstream PR.
