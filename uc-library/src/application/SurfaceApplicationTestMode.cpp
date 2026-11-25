#include "presonus/application/SurfaceApplication.hpp"

namespace Presonus::Surface {
void SurfaceApplication::setupAndRunTestMode(SurfaceTestMode mode) {
  testModeRequested_ = true;
  testMode_ = mode;
}
} // namespace Presonus::Surface
