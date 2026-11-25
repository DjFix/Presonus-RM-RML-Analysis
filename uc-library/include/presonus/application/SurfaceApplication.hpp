#pragma once
#include "core/portable/corefilename.h"
#include <cstdint>

namespace presonus::application {
struct SurfaceSerialStateAccess;
struct SurfaceTestModeReplayAccess;
} // namespace presonus::application
namespace Presonus::Surface {
// Source-port spelling for the observed 32-bit mode word.
enum class SurfaceTestMode : std::uint32_t;
// Partial source-port declaration only. The original constructor, lifetime,
// interfaces, inheritance and ARM32 object layout have not been recovered here.
class SurfaceApplication {
public:
  // Ordinary return spelling is unencoded; void remains declaration-pending.
  void readSerialFromDisk();
  // The original return declaration remains unresolved.
  void setupAndRunTestMode(SurfaceTestMode mode);
  // Source-port return word; the original return type remains unresolved.
  std::uint32_t isNetworkClientReady() const;
  // Numeric 64-bit returns are source-port choices; declarations remain
  // pending.
  std::uint64_t getAlternateMac();
  std::uint64_t getNetworkSerial();
  static Core::Portable::FileName getSkinDirectory();

private:
  friend struct presonus::application::SurfaceSerialStateAccess;
  friend struct presonus::application::SurfaceTestModeReplayAccess;
  std::uint32_t serial_;
  SurfaceTestMode testMode_{};
  bool testModeRequested_{};
};
} // namespace Presonus::Surface
namespace presonus::application {
// Independent fixture access, not an original PreSonus application interface.
struct SurfaceSerialStateAccess {
  static void seed(Presonus::Surface::SurfaceApplication &app,
                   std::uint32_t value) {
    app.serial_ = value;
  }
  static std::uint32_t value(const Presonus::Surface::SurfaceApplication &app) {
    return app.serial_;
  }
};
} // namespace presonus::application
