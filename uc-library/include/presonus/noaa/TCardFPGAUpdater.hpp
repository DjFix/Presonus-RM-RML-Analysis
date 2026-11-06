#pragma once
#include "presonus/noaa/sysex_receiver.hpp"
#include "presonus/uc/firmware_update_listener.hpp"
#include <array>

namespace Presonus {
class FirmwareBundle;
}
namespace presonus::noaa {
// Independent injectable boundary; the default uses actual CCL time, sleep,
// debug and the canonical SPI idle provider. This is not a recovered Core API.
class FpgaUpdaterServices : public presonus::dice::ResponseServices {
public:
  virtual void debugMessage(const char *message) = 0;
};
FpgaUpdaterServices &cclFpgaUpdaterServices();
void setFpgaProgressEpochMilliseconds(std::int64_t epoch);
} // namespace presonus::noaa
namespace Presonus::NOAA {
// Portable source model only: original field declarations, ordinary returns,
// object layout, ARM ABI and concurrency guarantees remain unresolved. The
// inherited response storage is shared with post/waitResponseSet. This class
// introduces its own virtual destructor; the existing receiver base is intact.
class TCardFPGAUpdater : public SysexReceiver {
public:
  TCardFPGAUpdater(UC::IFirmwareUpdateListener *, FirmwareBundle *);
  virtual ~TCardFPGAUpdater();
  bool accepts(const SysexPacket &) override;
  void receive(const SysexPacket &) override;
  void printProgress(const char *);
  void printProgressErr(const char *);
  // Portable coordinator definitions; ordinary original return declarations
  // remain unresolved. Partial image words use a zero-initialized seeded tail;
  // negative image read lengths fail closed instead of native out-of-bounds
  // access.
  bool waitFirmwareCommand(unsigned char *, int, const char *, long long);
  int update();
  // Independent setup/access; these names are not original recovered APIs.
  void setPortableServices(presonus::noaa::FpgaUpdaterServices &services) {
    services_ = &services;
    setPortableResponseServices(services);
  }
  void cancelPortableUpdate(bool value);

private:
  FirmwareBundle *bundle_;
  UC::IFirmwareUpdateListener *listener_;
  bool cancelled_ = false;
  std::array<unsigned char, 256> outbound_{};
  presonus::noaa::FpgaUpdaterServices *services_;
};
} // namespace Presonus::NOAA
