#pragma once
#include "core/public/corestringbuffer.h"
namespace presonus::uux {
struct PathsSourcePort {};
struct PathView;
} // namespace presonus::uux
namespace Presonus::UUX {
// Original interface scope/three slots witnessed by original app callback
// calls. void declarations provisional; no original ABI/lifetime claim.
class FirmwareUpdateListener {
public:
  virtual void doAlert(const char *, const char *, const char *) = 0;
  virtual void dismissAlert() = 0;
  virtual void onProgress(const char *, const char *, float) = 0;

protected:
  ~FirmwareUpdateListener() = default;
};
// Partial portable state only; original full fields/bases/lifetime unrecovered.
class FirmwareUpdater {
public:
  explicit FirmwareUpdater(presonus::uux::PathsSourcePort,
                           const char *localDirectory = "/home/root/DFU",
                           FirmwareUpdateListener *listener = nullptr,
                           bool animate = true)
      : listener(listener), animate(animate),
        localArchiveDirectory(localDirectory) {}
  // int return provisional: original ordinary mangling does not encode it.
  int setUsbImagePath(Core::CStringBuffer<256> &path);
  int setUuxUpgradeUrl(Core::CStringBuffer<256> &url);

  int doLocalFirmwareUpdate();
  int doUsbFirmwareUpdate();
  // Real POSIX/CCL backend bodies; validation intercepts all OS operations.
  int executeBashUpgradeScript(const char *command);
  int spinUpgradeDisplay(int process);

private:
  friend struct presonus::uux::PathView;
  FirmwareUpdateListener *listener;
  bool animate;
  Core::CString256 localArchiveDirectory;
  Core::CString256 usbImagePath;
  Core::CString256 upgradeUrl;
};
} // namespace Presonus::UUX
namespace presonus::uux {
// Independent observation API, not recovered original methods.
struct PathView {
  static Core::CString256 &usb(Presonus::UUX::FirmwareUpdater &updater) {
    return updater.usbImagePath;
  }
  static Core::CString256 &url(Presonus::UUX::FirmwareUpdater &updater) {
    return updater.upgradeUrl;
  }
};
} // namespace presonus::uux
