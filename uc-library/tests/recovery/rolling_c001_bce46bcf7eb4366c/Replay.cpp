#include "presonus/surface/CascadeHandler.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>

int main() {
  for (int iteration = 0; iteration < 3; ++iteration) {
    Presonus::Surface::SurfaceRootComponent root;
    Presonus::Surface::CascadeHandler handler(root);
    const auto &items = handler.items();
    if (items.count() != 0 || &handler.root() != &root)
      return 1;
    handler.onNetworkShutdown();
    if (items.count() != 0 || &handler.root() != &root)
      return 2;
    std::cout << "unchanged\n";
  }
}
