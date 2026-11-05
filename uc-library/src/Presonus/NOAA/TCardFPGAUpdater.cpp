#include "presonus/noaa/TCardFPGAUpdater.hpp"
#include "core/system/coredebug.h"
#include <cstring>

namespace {
// Independent epoch storage for this source port. Cross-class linkage to the
// firmware translation unit's gStartTicks is not established by this model.
std::int64_t epochMilliseconds = 0;
std::int64_t difference(std::int64_t a, std::int64_t b) {
  auto bits = static_cast<std::uint64_t>(a) - static_cast<std::uint64_t>(b);
  std::int64_t result;
  std::memcpy(&result, &bits, sizeof result);
  return result;
}
class CclServices final : public presonus::noaa::FpgaUpdaterServices,
                          private presonus::dice::IdlePump {
  presonus::dice::CclResponseServices response_{*this};
  void onIdle(bool force) override {
    Presonus::NOAA::TCardSPI::instance().onIdle(force);
  }

public:
  std::int64_t clockRawTicks() override { return response_.clockRawTicks(); }
  void pumpIdle(bool force) override { response_.pumpIdle(force); }
  void sleepMilliseconds(std::uint32_t value) override {
    response_.sleepMilliseconds(value);
  }
  void timeoutNotice(bool responseSet, std::uint32_t response,
                     std::uint32_t timeout) override {
    response_.timeoutNotice(responseSet, response, timeout);
  }
  void debugMessage(const char *message) override {
    Core::DebugPrintf("%s", message);
  }
};
} // namespace
namespace presonus::noaa {
FpgaUpdaterServices &cclFpgaUpdaterServices() {
  static CclServices services;
  return services;
}
void setFpgaProgressEpochMilliseconds(std::int64_t epoch) {
  epochMilliseconds = epoch;
}
} // namespace presonus::noaa
namespace Presonus::NOAA {
TCardFPGAUpdater::TCardFPGAUpdater(UC::IFirmwareUpdateListener *listener,
                                   FirmwareBundle *bundle)
    : bundle_(bundle), listener_(listener),
      services_(&presonus::noaa::cclFpgaUpdaterServices()) {
  setPortableResponseServices(*services_);
  TCardSPI::instance().registerReceiver(this);
}
TCardFPGAUpdater::~TCardFPGAUpdater() {
  TCardSPI::instance().unRegisterReceiver(this);
}
bool TCardFPGAUpdater::accepts(const SysexPacket &packet) {
  return packet.length > 1 && packet.bytes[1] >= 2 && packet.bytes[1] <= 5;
}
void TCardFPGAUpdater::receive(const SysexPacket &packet) {
  auto &state = portableState();
  state.command = packet.bytes[2];
  state.infoWords[0] = packet.bytes[3];
  state.status = packet.bytes[4];
}
void TCardFPGAUpdater::printProgress(const char *message) {
  if (listener_) {
    const auto now = services_->clockRawTicks() / 1000000;
    listener_->onProgress(
        message,
        static_cast<float>(difference(now, epochMilliseconds)) / 280000.f);
  }
  if (message && *message) {
    services_->debugMessage(message);
    services_->debugMessage("\n");
  }
}
void TCardFPGAUpdater::printProgressErr(const char *message) {
  printProgress(message);
  services_->sleepMilliseconds(2000);
}
} // namespace Presonus::NOAA
