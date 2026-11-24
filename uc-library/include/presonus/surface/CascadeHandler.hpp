#pragma once
#include "core/public/corevector.h"
namespace Presonus::UC {
class NetworkItem;
}
namespace Presonus::Surface {
class SurfaceRootComponent;
// Portable composition; original multiple inheritance/vtables/ARM layout
// unresolved.
class CascadeHandler {
public:
  explicit CascadeHandler(SurfaceRootComponent &);
  // Portable callback declaration; original return and virtual interface are
  // unresolved.
  void onNetworkShutdown();
  SurfaceRootComponent &root() const { return root_; }
  const Core::Vector<UC::NetworkItem *> &items() const { return items_; }

private:
  SurfaceRootComponent &root_; // borrowed, must outlive handler
  Core::Vector<UC::NetworkItem *> items_;
};
} // namespace Presonus::Surface
