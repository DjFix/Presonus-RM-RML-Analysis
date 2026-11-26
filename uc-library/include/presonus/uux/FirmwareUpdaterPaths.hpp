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
// Portable source port. Original complete layout/ARM ABI and unencoded return
// declarations remain unresolved; lifecycle bodies use genuine C++ variants.
class FirmwareUpdater {
public:
  explicit FirmwareUpdater(presonus::uux::PathsSourcePort,
                           const char *localDirectory = "/home/root/DFU",
                           FirmwareUpdateListener *listener = nullptr,
                           bool animate = true)
      : listener(listener), animate(animate),
        localArchiveDirectory(localDirectory) {}
  FirmwareUpdater(int product, int serial, FirmwareUpdateListener *listener);
  virtual ~FirmwareUpdater();
  int prepareFirmwareRequestFields();
  int doNetworkFirmwareUpdate();
  int updateFirmware();
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
  // Source-port state named by observed use, not original ARM field
  // declarations.
  Core::CString64 requestEndpoint;
  Core::CString64 completionMessage;
  Core::CString64 productId;
  Core::CString64 serialNumber;
  Core::CString64 macAddress;
  Core::CString64 firmwareVersion;
  Core::CString64 requestKey;
  Core::CString64 timestamp;
  Core::CString64 sourceFirmwareVersion{"13840"};
};
} // namespace Presonus::UUX
namespace presonus::uux {
// Independent observation API, not recovered original methods.
struct PathView {
  static bool animated(const Presonus::UUX::FirmwareUpdater &updater) {
    return updater.animate;
  }
  static Core::CString64 &requestField(Presonus::UUX::FirmwareUpdater &updater,
                                       unsigned index) {
    Core::CString64 *fields[] = {
        &updater.requestEndpoint, &updater.completionMessage,
        &updater.productId,       &updater.serialNumber,
        &updater.macAddress,      &updater.firmwareVersion,
        &updater.requestKey,      &updater.timestamp};
    return *fields[index];
  }
  static void firmwareVersion(Presonus::UUX::FirmwareUpdater &updater,
                              const char *version) {
    updater.sourceFirmwareVersion = version;
  }
  static void configureTask(Presonus::UUX::FirmwareUpdater &updater,
                            const char *endpoint) {
    updater.requestEndpoint = endpoint;
    updater.animate = false;
  }
  static Core::CString256 &usb(Presonus::UUX::FirmwareUpdater &updater) {
    return updater.usbImagePath;
  }
  static Core::CString256 &url(Presonus::UUX::FirmwareUpdater &updater) {
    return updater.upgradeUrl;
  }
};
} // namespace presonus::uux
