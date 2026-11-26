#include "presonus/application/SurfaceApplication.hpp"
#include "presonus/uc/ClientRootComponent.hpp"

namespace Presonus::Surface {
void SurfaceApplication::releaseClientComponent(
    UC::ClientRootComponent *client) {
  delete client;
}
} // namespace Presonus::Surface
