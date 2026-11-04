# This task’s reconstruction migration

Status: copied and hash-checked; original data retained pending user approval.

- [STM32 command map](../command-map/REPORT.md)
- [STM32 SPI receive results](../spi-rx/REPORT.md)
- [Embedded extraction report](../../app/embedded-extraction/REPORT.md)
- [Migration manifest](manifest.json)

Final job results are under `reconstruction/artifacts/<type>-<version>/<component>/`.
Logs and working notes are under the matching `reconstruction/evidence/` tree.
Extracted blobs retain their original names and container-version identity; this does
not imply embedded firmware shares the host’s application version.

Added components: `noaa-stm32-dice`, `noaa-fpga-dice`, `esa-stm32-dice`,
`esa-fpga-dice`, and `dice3` (surface internal DICE firmware).
The extraction batch’s shared provenance and tools live under mixer-13731/app;
its individual blobs are distributed by original input version/component.
No datasets owned by other agents were migrated.

Historical JSON proofs and scripts retain their original path strings and hashes.
Use manifest.json for path translation; Markdown navigation links were updated in
copies. This migration is a storage/layout check, not a new behavioral validation.

Root backup: `.backups/project-root-before-reconstruction.tar`. Its adjacent log lists
unreadable rootfs files outside this migration. All selected files were individually
verified against the backup before copying. The failed compressed attempt is retained
as `.partial.tar.gz`. No original paths were removed.
