# Reconstruction 10 × 10, 21 November 2026

The cycle admitted **100 distinct original ELF identities**. SQLite classifies 8 as portable-ready and 92 as compiled with original declarations pending. The admitted set has 91 demangled callable groups and 100 distinct mangled names. It includes 26 constructor or destructor variant identities. Ready status applies to the recorded portable validation domains. Original ARM ABI and hardware validation remain open.

89 admitted identities came from the initial selection and 11 were recorded replacements. The live journal also recorded 6,229 compatibility updates for existing identities, including possible repeats across admission waves. They carry no new reconstruction credit.

Local acceptance receipts cover 101 distinct identities across 101 passing and 0 failing check attempts. Verified source-application receipts cover 101 identities that reached the canonical checkout at least once. The Gate Page parameter callback remains parked after canonical reentry validation. The existing AudioComponent deleting-destructor audit carries no reconstruction credit.

## Elapsed time

| Clock | UTC or elapsed time |
| --- | ---: |
| Original request | 2026-11-20T23:39:26.291000+00:00 |
| Last operational gate | 2026-11-21T08:13:00.535526+00:00 |
| Request to operational end | 8:33:34.245 |

The post-commit receipt records the final elapsed time in `temp/recovery-work/reconstruction10x10-20261121/FINAL_TIMING.json`.

| Observed elapsed window | Duration |
| --- | ---: |
| Request to first observed worker launch | 0:52:49.372 |
| First observed worker launch to last recorded passing local acceptance | 6:42:05.385 |
| Last recorded passing local acceptance to operational end | 0:58:39.487 |

The two initial Docker mount failures took 561.540 s and 427.310 s, totaling 988.850 s in summed command time and about 563.343 s of calendar time. The union anchors measured command durations to final log timestamps. 2 other packet command receipts have no unambiguous outer timer and are excluded from measured intervals.

## Linux and SQLite

| CTest attempt | Passed | Total |
| --- | ---: | ---: |
| linux-g01-g09-01 | 806 | 811 |
| linux-g01-g06-g09-02 | 821 | 821 |
| linux-scoped30-03 | 845 | 851 |
| linux-scoped29-04 | 850 | 850 |
| linux-next31-05 | 875 | 881 |
| linux-next34-06 | 884 | 884 |
| linux-tail12-07 | 896 | 896 |

| Guarded SQLite admission | New IDs | Dry-run s | Live s |
| --- | ---: | ---: | ---: |
| union25-admission | 25 | 35.492 | 60.534 |
| scoped29-admission | 29 | 35.048 | 54.686 |
| next34-admission | 34 | 35.661 | 57.229 |
| tail12-admission | 12 | 36.076 | 56.051 |

The first live admission created one extra SQLite backup. Subsequent admissions used the verified VM101 rollback snapshot.

The completed Linux receipts include installed-role and artifact checks. Each admission window links its tracker, checkpoint and mirror audit when recorded.

## Live graph publication

| Attempt | Terminal state | Command wall | Recompiled | Reused captures | Staging writes MiB | Serialized requests MiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| actual01 | registered | 0:41:29.266 | 1340 | 0 | 892.8 | 382.5 |
| actual02 | registered | 0:53:45.528 | 1371 | 0 | 1,910.8 | 725.0 |
| actual03 | registered | 1:17:15.221 | 1410 | 0 | 2,939.2 | 1,010.4 |
| actual04 | registered | 0:54:58.088 | 1425 | 0 | 1,152.1 | 557.6 |

Graph command intervals total 3:47:28.090 of calendar time over a 7:03:50.860 first-start-to-last-end span. The graph commands overlapped 0:29:08.437 of measured Linux commands and 0:00:19.285 of local acceptance commands. Those overlaps already contribute to elapsed time. The request-byte column measures serialized request envelopes.

Actual 03 committed and registered during the first attempt. The initial postflight flagged 12 relinked CTest executables and the updated validation proof. A read-only follow-up checked the 13 outputs and confirmed the registered source generation. The original postflight exception remains in the evidence. Only one publication command ran for this window. Actual 04 also registered on its first command. Its initial postflight flagged a rebuilt graph-bound object. The read-only postflight reconciled the generated objects and archives to the registered generation at the final operational cutoff.

## Prior cycle comparison

The 16 November cycle took 7:42:59.611 through its operational gate and admitted 76 identities. It then spent 0:09:06.643 on reporting and commit work. Its graph attempts consumed 0:32:04.149 for the failed attempt and 1:02:39.038 for the successful retry. The cycles used different workloads, compiler reuse and admission windows. The measured elapsed times compare these two workloads. Estimating a causal speedup requires matching inputs.

## Local evidence

- Operational cutoff and elapsed intervals in `temp/recovery-work/reconstruction10x10-20261121/timing/FINAL_OPERATIONAL.json`
- Exact SQLite admissions and original identities in `temp/recovery-work/reconstruction10x10-20261121/timing/LIVE100_FINAL.json`
- Per-command Linux and SQLite wall/CPU receipts in `evidence/recovery/2026-11-21/reconstruction10x10/INTEGRATION_TIMING_INDEX_CYCLE100.json`
- Graph command, registration and publication receipts under `temp/recovery-work/reconstruction10x10-20261121/graph/`
- Linux, admission, tracker, checkpoint and mirror receipts under `evidence/recovery/2026-11-21/reconstruction10x10/`
