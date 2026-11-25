#include "presonus/application/SurfaceApplication.hpp"

#include <cstring>
#include <iostream>

namespace presonus::application {
struct SurfaceTestModeReplayAccess {
  static bool run(std::uint32_t serial, std::uint32_t initialMode,
                  bool initialRequested, std::size_t count) {
    using namespace Presonus::Surface;
    SurfaceApplication app{};
    app.serial_ = serial;
    app.testMode_ = static_cast<SurfaceTestMode>(initialMode);
    app.testModeRequested_ = initialRequested;
    for (std::size_t index = 0; index < count; ++index) {
      std::uint32_t mode;
      if (!(std::cin >> mode))
        return false;
      unsigned char expected[sizeof(app)];
      std::memcpy(expected, &app, sizeof(app));
      app.setupAndRunTestMode(static_cast<SurfaceTestMode>(mode));
      const auto *bytes = reinterpret_cast<const unsigned char *>(&app);
      const auto modeOffset =
          reinterpret_cast<const unsigned char *>(&app.testMode_) - bytes;
      const auto requestedOffset =
          reinterpret_cast<const unsigned char *>(&app.testModeRequested_) -
          bytes;
      std::memcpy(expected + modeOffset, &app.testMode_, sizeof(app.testMode_));
      std::memcpy(expected + requestedOffset, &app.testModeRequested_,
                  sizeof(app.testModeRequested_));
      std::cout << static_cast<std::uint32_t>(app.testMode_) << ' '
                << app.testModeRequested_ << ' ' << app.serial_ << ' '
                << (std::memcmp(expected, &app, sizeof(app)) == 0) << '\n';
    }
    return true;
  }
};
} // namespace presonus::application

int main() {
  std::uint32_t serial;
  std::uint32_t initialMode;
  bool initialRequested;
  std::size_t count;
  while (std::cin >> serial >> initialMode >> initialRequested >> count) {
    if (!presonus::application::SurfaceTestModeReplayAccess::run(
            serial, initialMode, initialRequested, count))
      return 1;
  }
  return std::cin.eof() ? 0 : 1;
}
