// NONPRODUCTION, UNVALIDATED: preserved method proposal. Never built by the
// active handoffs. Native execution remains parked. Shared epoch linkage must
// be restored deliberately on approved reintegration; this is not a provider.
#include "core/public/corestringbuffer.h"
#include "presonus/application/ResourceLibrary.hpp"
#include "presonus/dice/codec.hpp"
#include "presonus/noaa/TCardFPGAUpdater.hpp"
#include <cstring>
namespace {
extern std::int64_t
    epochMilliseconds; // shared active progress epoch, unresolved here
std::uint32_t progressCadence = 0;
std::int64_t plus(std::int64_t a, unsigned b) {
  auto bits = static_cast<std::uint64_t>(a) + b;
  std::int64_t result;
  std::memcpy(&result, &bits, sizeof result);
  return result;
}
} // namespace
namespace Presonus::NOAA {
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
  epochMilliseconds = services_->clockRawTicks() / 1000000;
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
      unsigned value;
      std::memcpy(&value, block.data() + 4 * i, 4);
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
      Core::CString128 message;
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
      Core::CString128 message;
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
    Core::CString128 message;
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
