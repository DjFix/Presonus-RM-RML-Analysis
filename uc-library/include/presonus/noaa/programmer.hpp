#pragma once
#include "presonus/uc/firmware_update_listener.hpp"
#include <array>
#include <cstdint>
#include <termios.h>

namespace Presonus::UC {
class IFirmwareUpdateListener;
}
namespace presonus::noaa {
// Independent POSIX transport boundary. Production forwards actual write/close;
// offline fixtures provide explicit return/error scripts, never device success.
class ProgrammerTransport {
public:
  virtual ~ProgrammerTransport() = default;
  virtual std::int32_t write(std::int32_t descriptor, const unsigned char *data,
                             std::uint32_t count) = 0;
  virtual std::int32_t close(std::int32_t descriptor) = 0;
};
ProgrammerTransport &posixProgrammerTransport();

// Independent shared byte storage, not the original class layout. Actual app
// ranges place the128-byte response at+0x2c and outbound count/payload
// at+0xac/+0xad. Thus the129th response terminator and packet count must be the
// SAME byte.
class ProgrammerResponseStorage {
  std::array<unsigned char, 385> storage_{};

public:
  unsigned char *data() { return storage_.data(); }
  const unsigned char *data() const { return storage_.data(); }
  unsigned char &operator[](std::size_t index) { return storage_[index]; }
  const unsigned char &operator[](std::size_t index) const {
    return storage_[index];
  }
  unsigned char *begin() { return data(); }
  const unsigned char *begin() const { return data(); }
  unsigned char *end() { return data() + 129; }
  const unsigned char *end() const { return data() + 129; }
  void fill(unsigned char value) {
    for (std::size_t i = 0; i < 129; ++i)
      storage_[i] = value;
  }
  unsigned char *packetData() { return data() + 128; }
  const unsigned char *packetData() const { return data() + 128; }
};
// Independent portable state; original private declarations/layout unresolved.
struct TCardProgrammerState {
  std::int32_t descriptor = -1;
  const unsigned char *image = nullptr;
  unsigned int length = 0;
  Presonus::UC::IFirmwareUpdateListener *listener = nullptr;
  std::uint32_t word16 = 115200;
  unsigned char byte24 = 0;
  std::array<std::uint32_t, 4> words28to40{};
  // Original writes a terminator at buffer+128 for its128th byte.
  ProgrammerResponseStorage response{};
};
class ProgrammerReceiveServices {
public:
  virtual ~ProgrammerReceiveServices() = default;
  virtual std::int64_t clockRawTicks() = 0;
  virtual std::int32_t readByte(std::int32_t descriptor,
                                unsigned char *byte) = 0;
  virtual void responseTimeout() = 0;
  virtual void responseReadError(std::int32_t value) = 0;
  virtual void debugMessage(const char *message) = 0;
};
ProgrammerReceiveServices &posixProgrammerReceiveServices();
class ProgrammerInformationServices {
public:
  virtual ~ProgrammerInformationServices() = default;
  virtual void partID(std::uint32_t value) = 0;
  virtual void bootloaderVersion(std::uint32_t major, std::uint32_t minor) = 0;
  virtual void eraseCommand(unsigned char value) = 0;
};
ProgrammerInformationServices &cclProgrammerInformationServices();
class ProgrammerSerialServices {
public:
  virtual ~ProgrammerSerialServices() = default;
  virtual std::int32_t openPath(const char *path, int flags) = 0;
  virtual int getAttributes(int descriptor, termios &value) = 0;
  virtual int flushInput(int descriptor) = 0;
  virtual int setAttributes(int descriptor, const termios &value) = 0;
  virtual int lastError() = 0;
  virtual void openError(const char *path, int error) = 0;
};
ProgrammerSerialServices &posixProgrammerSerialServices();
struct ProgrammerAccess;
} // namespace presonus::noaa

namespace Presonus::NOAA {
// Original RTTI is a root class; its two virtual slots are D1/D0. Source-port
// state/provider storage is not the original ARM32 layout or serial setup.
class TCardProgrammer {
public:
  TCardProgrammer(UC::IFirmwareUpdateListener *, const unsigned char *,
                  unsigned int);
  virtual ~TCardProgrammer();

  // Encoded member/parameter identities established from actual app bodies.
  // Ordinary uint32/int32 return declarations remain explicitly unresolved.
  std::uint32_t calcCRC(const unsigned char *data, int length);
  std::int32_t write(const unsigned char *data, int length);
  std::int32_t writeChar(unsigned char value);
  std::int32_t sendPacket(const unsigned char *data, int length);
  std::int32_t sendAddress(unsigned int address);
  std::int32_t close();
  std::int32_t waitResponse(int timeout);
  std::int32_t getNextChar(int timeout);
  std::int32_t waitAck(int timeout);
  std::int32_t sync();
  std::int32_t doCommand(unsigned char command);
  void printProgress(const char *message, bool emit);
  void printInfo();
  std::int32_t getChipID();
  std::int32_t readInfo();
  std::int32_t openPort(const char *path);
  std::int32_t open(const char *path);

private:
  friend struct presonus::noaa::ProgrammerAccess;
  presonus::noaa::TCardProgrammerState state_;
  presonus::noaa::ProgrammerTransport *transport_;
  presonus::noaa::ProgrammerReceiveServices *receive_ = nullptr;
  presonus::noaa::ProgrammerInformationServices *information_ = nullptr;
  presonus::noaa::ProgrammerSerialServices *serial_ = nullptr;
};
} // namespace Presonus::NOAA

namespace presonus::noaa {
// Independent caller/test setup; no original setter/interface claim.
struct ProgrammerAccess {
  static void bind(Presonus::NOAA::TCardProgrammer &object,
                   ProgrammerTransport &transport, std::int32_t descriptor) {
    object.transport_ = &transport;
    object.state_.descriptor = descriptor;
  }
  static void bindSerial(Presonus::NOAA::TCardProgrammer &object,
                         ProgrammerSerialServices &services) {
    object.serial_ = &services;
  }
  static void bindInformation(Presonus::NOAA::TCardProgrammer &object,
                              ProgrammerInformationServices &services) {
    object.information_ = &services;
  }
  static void bindReceive(Presonus::NOAA::TCardProgrammer &object,
                          ProgrammerReceiveServices &services) {
    object.receive_ = &services;
  }
  static TCardProgrammerState &
  mutableState(Presonus::NOAA::TCardProgrammer &object) {
    return object.state_;
  }
  static const TCardProgrammerState &
  state(const Presonus::NOAA::TCardProgrammer &object) {
    return object.state_;
  }
};
} // namespace presonus::noaa

namespace presonus::noaa {
// Independent fixture/source-port state bridge, not an original interface.
void setProgrammerProgressEpochMilliseconds(std::int64_t value);
} // namespace presonus::noaa
