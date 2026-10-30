#include "core/portable/corefile.h"
#include "core/system/coredebug.h"
#include "presonus/uux/FirmwareUpdaterPaths.hpp"
namespace Presonus::UUX {
int FirmwareUpdater::doLocalFirmwareUpdate() {
  Core::DebugPrintf("FirmwareUpdater attempting local firmware upgrade...\n");
  if (!Core::Portable::FileUtils::fileExists(localArchiveDirectory.str())) {
    Core::DebugPrintf("\t!! local upgrade failed: no local archive\n");
    return 2;
  }
  Core::CString64 command;
  command.appendFormat("./fw-local-upgrade.sh");
  const int result =
      spinUpgradeDisplay(executeBashUpgradeScript(command.str()));
  Core::DebugPrintf("Firmware script result: %d\n", result);
  return result;
}
int FirmwareUpdater::doUsbFirmwareUpdate() {
  if (!Core::Portable::FileUtils::fileExists(usbImagePath.str()))
    return 2;
  Core::CString64 command;
  command.appendFormat("./fw-upgrade.sh");
  const int result =
      spinUpgradeDisplay(executeBashUpgradeScript(command.str()));
  Core::DebugPrintf("Firmware script result: %d\n", result);
  return result;
}
} // namespace Presonus::UUX
