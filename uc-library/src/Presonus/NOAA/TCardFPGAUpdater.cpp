#include "presonus/noaa/TCardFPGAUpdater.hpp"
#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/dice/codec.hpp"
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
std::uint32_t progressCadence = 0;
std::int64_t plus(std::int64_t a, unsigned b) {
  auto bits = static_cast<std::uint64_t>(a) + b;
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
void TCardFPGAUpdater::cancelPortableUpdate(bool value) { cancelled_ = value; }
bool TCardFPGAUpdater::waitFirmwareCommand(unsigned char *command, int length,
                                           const char *message,
                                           long long timeout) {
  auto &state = portableState();
  state.command = state.status = 0;
  state.infoWords[0] = 0;
  if (!command || length == 0) {
    if (message && *message)
      printProgress(message);
    return waitResponseSet(state.infoWords[0], timeout);
  }
  printProgress(message);
  SysexPacket packet(command, static_cast<unsigned char>(length));
  post(packet);
  const auto start = services_->clockRawTicks() / 1000000;
  std::int64_t nextProgress = 0;
  while (true) {
    if (cancelled_) {
      printProgressErr("DFU ERROR #5");
      return false;
    }
    if (!timeout || state.command)
      return true;
    const auto elapsed =
        difference(services_->clockRawTicks() / 1000000, start);
    if (elapsed >= timeout) {
      printProgressErr("DFU ERROR #5");
      return false;
    }
    if (nextProgress == 0)
      nextProgress = plus(elapsed, 1000);
    else if (elapsed > nextProgress) {
      nextProgress = plus(elapsed, 300);
      printProgress(message);
    }
  }
}
int TCardFPGAUpdater::update() {
  presonus::noaa::setFpgaProgressEpochMilliseconds(services_->clockRawTicks() /
                                                   1000000);
  services_->debugMessage("TCardUpdater::updateFPGA\n");
  outbound_[0] = 0xf0;
  outbound_[1] = 2;
  outbound_[2] = 1;
  outbound_[3] = 0xf7;
  printProgress("Erasing Flash");
  auto &state = portableState();
  if (!waitFirmwareCommand(outbound_.data(), 4, "Erasing Flash", 60000) ||
      state.infoWords[0] != 0x7f || state.status) {
    printProgressErr("Error erasing flash");
    return 2000;
  }
  outbound_[1] = 3;
  if (bundle_->openBinImage() != 0)
    return 2003;
  printProgress("Writing FPGA");
  unsigned sequence = 0;
  std::uint32_t total = 0;
  // Original rounded-word read consumes prior stack tail bytes. The source port
  // defines an initialized zero tail and retains prior-block bytes thereafter.
  // Equivalence excludes partial words unless the native tail is seeded alike.
  std::array<unsigned char, 200> block{};
  while (true) {
    outbound_[3] = static_cast<unsigned char>(sequence);
    const int count = bundle_->readBinImageBlock(block.data(), 200);
    // Negative native read results can turn into huge unsigned word counts.
    // Fail closed rather than reproduce an out-of-bounds stack access.
    if (count < 0 || count > 200) {
      bundle_->closeBinImage();
      return 2003;
    }
    const unsigned words = (static_cast<unsigned>(count) + 3) / 4;
    for (unsigned i = 0; i < words; ++i) {
      // Original ARM image words are little endian regardless of host order.
      const auto *bytes = block.data() + 4 * i;
      const unsigned value = unsigned(bytes[0]) | (unsigned(bytes[1]) << 8) |
                             (unsigned(bytes[2]) << 16) |
                             (unsigned(bytes[3]) << 24);
      pack32(value, outbound_.data() + 4 + 5 * i);
    }
    outbound_[4 + 5 * words] = 0xf7;
    if (!waitFirmwareCommand(outbound_.data(), 5 * (words + 1), "", 4000)) {
      printProgressErr("Error: Flash timed out");
      return 2000;
    }
    total += static_cast<unsigned>(count);
    const auto oldCadence = progressCadence++;
    if (static_cast<std::int32_t>(oldCadence) > 20) {
      progressCadence = 1;
      Core::CStringBuffer<64> message;
      message.appendFormat("Writing FPGA:%08X", total);
      printProgress(message.getBuffer());
    }
    if (state.status) {
      printProgressErr("CRC ERR");
      bundle_->closeBinImage();
      return 2003;
    }
    if (state.infoWords[0] != sequence) {
      printProgressErr("CRC ERR2");
      Core::CStringBuffer<64> message;
      message.appendFormat("Image Program - Seq: expected %i, got> %i\n",
                           sequence, state.infoWords[0]);
      services_->debugMessage(message.getBuffer());
      bundle_->closeBinImage();
      return 2003;
    }
    sequence = (sequence + 1) & 127;
    if (count < 200)
      break;
  }
  bundle_->closeBinImage();
  outbound_[1] = 5;
  outbound_[3] = 0xf7;
  if (!waitFirmwareCommand(outbound_.data(), 4, "Finishing Stage", 4000)) {
    printProgressErr("Flash timed out");
    return 2003;
  }
  if (state.status || state.infoWords[0] != sequence) {
    Core::CStringBuffer<64> message;
    if (state.status)
      message.appendFormat("dfu error %d", state.status);
    else
      message.appendFormat("dfu error2 %d", state.infoWords[0]);
    printProgressErr(message.getBuffer());
    return 2005;
  }
  printProgress("Programming successful.");
  services_->sleepMilliseconds(1000);
  return 0;
}
} // namespace Presonus::NOAA
