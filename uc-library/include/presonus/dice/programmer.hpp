#pragma once

#include "presonus/dice/programmer_services.hpp"
#include <cstdint>

namespace Presonus::UC {
class IFirmwareUpdateListener;
}

namespace presonus::dice {
class ProgrammerDeviceServices;
// Independent callback boundary. The original listener's slot-zero name and
// parameters are established, but its return declaration is not recovered.
class ProgressSink {
public:
  virtual ~ProgressSink() = default;
  virtual void report(Presonus::UC::IFirmwareUpdateListener *listener,
                      const char *text, float value) = 0;
};

struct ProgrammerState {
  std::int32_t descriptor;
  const unsigned char *image;
  unsigned int length;
  Presonus::UC::IFirmwareUpdateListener *listener;
};
} // namespace presonus::dice

namespace Presonus::DICE {
// Portable source port. No old layout, device ownership or ARM ABI claim.
class Dice3Programmer {
public:
  // ARM spills four aggregate words, not an enum. Member names, native pointer
  // width and pointee/count declaration choices below are independent ports.
  struct mp25Transaction {
    const unsigned char *portableTransmit;
    std::uint32_t portableTransmitLength;
    unsigned char *portableReceive;
    std::uint32_t portableReceiveLength;
  };
  // Original ordinary returns remain unresolved; int32 is provisional.
  std::int32_t performTransaction(mp25Transaction transaction);
  std::int32_t writeEnable();
  std::int32_t busyWait(int timeout);
  std::int32_t readJedecId();
  // CANDIDATE ordinary return declarations, not established original types.
  std::int32_t open(const char *path);
  void close();
  // CANDIDATE int32 ordinary returns; declaration evidence remains pending.
  std::int32_t eraseAll();
  std::int32_t eraseSector(int sector);
  std::int32_t update();

  // Independent required borrowed device/GPIO provider, no original API claim.
  void bindProgrammerDeviceServices(
      presonus::dice::ProgrammerDeviceServices &services) {
    deviceServices_ = &services;
  }

  // CANDIDATE int32 returns; original ordinary declarations stay unresolved.
  std::int32_t dumpPage(int page);
  std::int32_t verifyPage(int page, const unsigned char *data, int length);
  std::int32_t writePage(int page, const unsigned char *data, int length);

  // Independent borrowed setup, not original descriptor ownership/lifecycle.
  void bindProgrammerServices(presonus::dice::ProgrammerServices &services,
                              std::int32_t descriptor) {
    services_ = &services;
    state_.descriptor = descriptor;
  }
  Dice3Programmer(UC::IFirmwareUpdateListener *listener,
                  const unsigned char *image, unsigned int length);
  ~Dice3Programmer();

  // The original body returns zero without inspecting the firmware image.
  // int is a portable numeric choice; the original return spelling is
  // unencoded.
  int verify();

  // Candidate void declaration only: original return type remains unresolved.
  // A non-null listener requires a previously bound portable ProgressSink.
  void printProgress(const char *text, float value, bool force);

  void bindProgressSink(presonus::dice::ProgressSink &sink) {
    progress_ = &sink;
  }
  presonus::dice::ProgrammerState inspectState() const { return state_; }

private:
  presonus::dice::ProgrammerState state_;
  presonus::dice::ProgressSink *progress_ = nullptr;
  presonus::dice::ProgrammerServices *services_ = nullptr;
  presonus::dice::ProgrammerDeviceServices *deviceServices_ = nullptr;
};
} // namespace Presonus::DICE
