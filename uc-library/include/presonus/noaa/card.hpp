#pragma once
#include "presonus/device_dfu.hpp"
#include "presonus/noaa/setup_property.hpp"
#include "presonus/noaa/sysex_receiver.hpp"
#include <array>
#include <cstdint>
#include <optional>
namespace Presonus::Dsp {
class IAudioHAL;
}
namespace Presonus {
class ResourceLibrary;
class FirmwareBundle;
} // namespace Presonus
namespace presonus::noaa {
// Independent explicit state, not an ARM object representation. Original field
// declarations/ownership remain unresolved. All access is caller-serialized.
struct CardState {
  std::uint32_t observedWord14;
  std::uint32_t observedWord40;
  std::uint32_t observedWord44;
  unsigned char observedByte48;
  OpaqueSetupReference opaque5c;
  std::uint32_t observedWord30;
  OpaqueSetupReference opaque2c;
  // Independent status projection; names identify observed ARM offsets only.
  std::uint32_t observedWord18{}, observedWord1c{}, observedWord20{},
      observedWord24{}, observedWord28{};
  std::uint32_t observedWord34{}, observedWord38{}, observedWord3c{};
  std::uint32_t observedWord4c{}, observedWord50{}, observedWord54{},
      observedWord58{};
  // Required only for new status/resource methods. Borrowed real library and
  // its bundles outlive all calls; bind before publication. Null is a
  // precondition failure, not a successful substitute for the original static
  // library.
  Presonus::ResourceLibrary *resources = nullptr;
  // Independent app-byte shadow corresponding only to original offsets60..67.
  // geqInit writes first7bytes and preserves seeded byte7. No ARM layout claim.
  std::array<unsigned char, 8> commandShadow{};
  // Independent borrowed bindings. Never cast/dereference either opaque setup
  // reference. Bind a live already-adjusted mutable HAL; compare identity only
  // immediately before an original HAL call. Owner outlives calls and
  // callbacks.
  Presonus::Dsp::IAudioHAL *audioHal = nullptr;
  // Original word2c is used numerically by receive; keep that explicit source-
  // port projection separate from the unchanged opaque2c copy. No zero
  // fallback.
  std::optional<std::uint32_t> expectedSerial;
};
struct CardSetupTag {};
inline constexpr CardSetupTag cardSetupTag{};
} // namespace presonus::noaa
namespace Presonus::NOAA {
struct NOAAStatusProperty;
// Original RTTI establishes these two bases. Original secondary adjustor thunks
// use ARM offset12; native layout/offsets are intentionally not claimed.
class TCard : public SysexReceiver, public Presonus::IDeviceDFU {
public:
  // Independent required setup; does not replace original C1/C2. Services,
  // opaque references and state outlive calls; providers must be injected
  // before first SPI singleton use when testing. Production can access actual
  // devices.
  TCard(presonus::noaa::CardSetupTag, presonus::noaa::CardState &state,
        presonus::dice::ResponseServices &response,
        presonus::noaa::SpiServiceIO &diagnostics)
      : state_(state), diagnostics_(diagnostics) {
    setPortableResponseServices(response);
  }
  // Independent modern cleanup only, not recovered original D1/D0 behavior.
  virtual ~TCard() = default;
  void receive(const SysexPacket &) override;
  bool accepts(const SysexPacket &) override;
  // Original table points to the existing SysexReceiver::post implementation.
  bool isMounted() override;
  bool isFirmwareCompatible(int) override;
  void getStatusProperty(NOAAStatusProperty &);
  Presonus::FirmwareBundle *getArmFirmwareBundle();
  Presonus::FirmwareBundle *getFpgaFirmwareBundle();
  bool updateFirmware(UC::IFirmwareUpdateListener *, int) override = 0;
  int open(const NOAASetupProperty &);
  bool start(bool force);
  unsigned char doCommand(unsigned char command, const char *notice);
  unsigned char setClockSource(int clock);
  unsigned char geqInit(unsigned char slot, unsigned char mode);
  unsigned char sendSampleRate(int rate, int link);
  void printStatus();
  unsigned int generateAlternateMac(unsigned int serial);
  unsigned char isDesktopConnected();
  const char *getCardCString();

private:
  presonus::noaa::CardState &state_;
  presonus::noaa::SpiServiceIO &diagnostics_;
};
} // namespace Presonus::NOAA
