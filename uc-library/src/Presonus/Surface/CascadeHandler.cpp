#include "presonus/surface/CascadeHandler.hpp"
namespace Presonus::Surface {
CascadeHandler::CascadeHandler(SurfaceRootComponent &root)
    : root_(root), items_(0, 5) {}
} // namespace Presonus::Surface
