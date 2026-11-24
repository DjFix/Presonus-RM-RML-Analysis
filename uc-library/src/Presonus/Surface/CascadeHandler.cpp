#include "presonus/surface/CascadeHandler.hpp"
namespace Presonus::Surface {
CascadeHandler::CascadeHandler(SurfaceRootComponent &root)
    : root_(root), items_(0, 5) {}
void CascadeHandler::onNetworkShutdown() {}
void CascadeHandler::onNetworkItemReleased(UC::NetworkItem *) {}
} // namespace Presonus::Surface
