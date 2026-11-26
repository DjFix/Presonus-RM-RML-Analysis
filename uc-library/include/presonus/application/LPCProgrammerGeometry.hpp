#pragma once
#include "presonus/uc/firmware_update_listener.hpp"
#include <array>
#include <cstdint>

namespace presonus::lpc {
// Independent construction tag for the geometry-only portable fixture.
struct GeometryOnly {};
// Explicit source-port state mapping: names identify observed ARM offsets,
// not recovered original field names or native object-layout guarantees.
struct ImageGeometryState {
  std::uint32_t raw08{}, raw18{}, raw30{}, raw34{}, raw38{}, raw40{}, raw48{},
      raw4c{};
};
struct ImageStateOnly {};
struct ImageGeometryAccess;
struct InputOnly {};
struct InputState {
  int descriptor{-1};
  std::array<char, 129> response{};
};
struct InputAccess;
struct IdentityOnly {};
struct DeviceIdentityState {
  std::array<std::uint32_t, 4> raw1c_to28{};
  std::uint32_t raw2c{};
};
struct DeviceIdentityAccess;
} // namespace presonus::lpc

namespace Presonus {
// Portable source state; original field declarations, bases and ARM layout
// remain unresolved. Ordinary return declarations below are provisional.
class LPCProgrammer {
public:
  LPCProgrammer(const unsigned char *image, unsigned size);
  virtual ~LPCProgrammer();
  int open(const char *path);
  void printInfo();
  void printProgress(const char *message);
  int unlockFlash();
  int prepareSector(unsigned first, unsigned last);
  int eraseSector(unsigned first, unsigned last);
  int eraseAll();
  int copyRAM2Flash(unsigned destination, unsigned source, unsigned size);
  // Input storage must cover the original encoder's padded reads (see replay).
  int writeRAM(unsigned address, unsigned size, unsigned char *data);
  int update(UC::IFirmwareUpdateListener *listener);
  explicit LPCProgrammer(presonus::lpc::GeometryOnly) noexcept {}
  // Original mangling establishes member scope/argument, but not return type.
  // unsigned is a provisional portable declaration; declaration remains
  // pending.
  unsigned getLastSector(unsigned part);
  explicit LPCProgrammer(
      presonus::lpc::ImageStateOnly,
      const presonus::lpc::ImageGeometryState &initial) noexcept
      : imageState(initial) {}
  // Original return declaration unencoded; int remains provisional.
  int initAddresses();
  explicit LPCProgrammer(presonus::lpc::InputOnly,
                         const presonus::lpc::InputState &initial) noexcept
      : inputState(initial) {}
  // Ordinary returns remain provisional; argument/member scopes preserved.
  int getNextChar(int timeout);
  int waitResponse(int timeout);
  int waitResult(int expected, int timeout);
  explicit LPCProgrammer(
      presonus::lpc::IdentityOnly, const presonus::lpc::InputState &input,
      const presonus::lpc::ImageGeometryState &image,
      const presonus::lpc::DeviceIdentityState &identity) noexcept
      : imageState(image), inputState(input), deviceIdentity(identity) {}
  // Original ordinary return declarations remain provisional.
  int writeString(const char *text);
  int waitValue(const char *command, int timeout);
  int readInfo();
  // Provisional returns; original ordinary declarations remain unresolved.
  int openPort(const char *path);
  int writeChar(unsigned char value);
  int close();
  int waitAnswerStr(const char *expected, int timeout);
  int writeStringReply(const char *text, int timeout);
  int sync();

private:
  friend struct presonus::lpc::ImageGeometryAccess;
  friend struct presonus::lpc::InputAccess;
  friend struct presonus::lpc::DeviceIdentityAccess;
  // Fixture-only partial constructors retain their prior non-owning lifetime.
  bool originalLifecycle{};
  const unsigned char *borrowedImage{};
  UC::IFirmwareUpdateListener *listener{};
  std::uint32_t baudRate{115200}, ramAddress{0x10000400},
      commandTimeout{100000};
  // Extra storage explicitly maps the response bytes read by the native
  // encoder.
  std::array<unsigned char, 520> block{};
  presonus::lpc::ImageGeometryState imageState{};
  presonus::lpc::InputState inputState{};
  presonus::lpc::DeviceIdentityState deviceIdentity{};
};
} // namespace Presonus

namespace presonus::lpc {
struct ImageGeometryAccess {
  static ImageGeometryState &state(Presonus::LPCProgrammer &programmer) {
    return programmer.imageState;
  }
};
} // namespace presonus::lpc

namespace presonus::lpc {
struct InputAccess {
  static InputState &state(Presonus::LPCProgrammer &p) { return p.inputState; }
};
} // namespace presonus::lpc

namespace presonus::lpc {
struct DeviceIdentityAccess {
  static DeviceIdentityState &state(Presonus::LPCProgrammer &p) {
    return p.deviceIdentity;
  }
};
} // namespace presonus::lpc
