#include "presonus/surface/CascadeHandler.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cassert>
#include <iostream>
int main() {
  for (int i = 0; i < 8; ++i) {
    Presonus::Surface::SurfaceRootComponent root;
    Core::Vector<Presonus::UC::NetworkItem *> provider(0, 5);
    Presonus::Surface::CascadeHandler actual(root);
    assert(&actual.root() == &root);
    assert(actual.items().count() == provider.count());
    assert(actual.items().getCapacity() == provider.getCapacity());
    assert(actual.items().getDelta() == provider.getDelta());
    assert(actual.items().getItems() == nullptr);
  }
  std::cout << "8 valid-root actual-provider cases passed\n";
}
