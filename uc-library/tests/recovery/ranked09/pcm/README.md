# Pcm4104Spi constructor investigation

`oracle.py` verifies the CS18AI surface 13840 ELF SHA-256 and each independent
C1/C2 60-byte section-12 range, then executes the original ARM instructions with
Unicorn 2.1.4. Twenty-four cases cover four prior object byte patterns and null,
empty and nonempty name pointers. Execution stops at the unresolved `open`
entry, before executing any provider or touching a device. Observations capture
the argument registers and 32 bytes surrounding constructor initialization.

Run from the repository root:

```
uc-library/.venv/bin/python uc-library/tests/recovery/ranked09/pcm/oracle.py temp/recovery-work/ranked-trial-09-small01/worker-pcm/native-boundary.json
```

This is bounded native evidence, not a C++ reconstruction or replay. It does not
validate open behavior, constructor completion, resource ownership, destructor
cleanup, layout, ABI or hardware interoperability. No production constructor is
provided while the required callable behavior remains unresolved.
