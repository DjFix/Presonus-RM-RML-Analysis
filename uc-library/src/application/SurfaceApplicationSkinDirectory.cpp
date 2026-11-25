#include "presonus/application/SurfaceApplication.hpp"

namespace Presonus::Surface {
Core::Portable::FileName SurfaceApplication::getSkinDirectory() {
  return Core::Portable::FileName("/media/skin");
}
} // namespace Presonus::Surface
