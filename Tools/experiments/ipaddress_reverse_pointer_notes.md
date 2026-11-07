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

## Decision after reading upstream discussion (November 2026)

An existing upstream PR, https://github.com/python/cpython/pull/29011,
remains **open** and already fixes network reverse pointers by constructing
reverse DNS zones from aligned IPv4 octet/IPv6 nibble prefixes, raising
NetmaskValueError for unaligned lengths. Earlier alternative PRs #3632
and #25371 were closed without merging. This is not a free upstream issue.

Core developer Ronald Oussoren pointed out in issue #74713 that a network
has no single PTR query name and that raising instead may be preferable.
Issue #125641 explores a separate `reverse_pointers` collection API to
represent unaligned networks. Neither approach has consensus.

**Therefore do not open a competing PR for #91601.** The reproducer in
this branch remains useful for reviewing #29011 or a future agreed design.
For the second independent contribution, prioritize a distinct, scoped bug
or test-coverage issue with no active competing PR.
