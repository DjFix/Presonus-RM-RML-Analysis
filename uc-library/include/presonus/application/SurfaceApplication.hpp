#pragma once
#include <cstdint>

namespace presonus::application {
struct SurfaceSerialStateAccess;
}
namespace Presonus::Surface {
// Partial source-port declaration only. The original constructor, lifetime,
// interfaces, inheritance and ARM32 object layout have not been recovered here.
class SurfaceApplication {
public:
  // Ordinary return spelling is unencoded; void remains declaration-pending.
  void readSerialFromDisk();
  // Numeric 64-bit returns are source-port choices; declarations remain
  // pending.
  std::uint64_t getAlternateMac();
  std::uint64_t getNetworkSerial();

private:
  friend struct presonus::application::SurfaceSerialStateAccess;
  std::uint32_t serial_;
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
