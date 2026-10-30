#include "presonus/uux/FirmwareUpdaterPaths.hpp"
#include <cstring>
namespace Presonus::UUX {
int FirmwareUpdater::setUsbImagePath(Core::CStringBuffer<256> &path) {
  if (std::strlen(path.str()) > 255)
    return -1;
  std::memcpy(usbImagePath.getBuffer(), path.str(), 256);
  return 0;
}
int FirmwareUpdater::setUuxUpgradeUrl(Core::CStringBuffer<256> &url) {
  if (std::strlen(url.str()) > 255)
    return -1;
  std::memcpy(upgradeUrl.getBuffer(), url.str(), 256);
  return 0;
}
} // namespace Presonus::UUX
