#include "presonus/surface/CascadeHandler.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include "presonus/uc/NetworkItem.hpp"
#include <iostream>
#include <string_view>

int main() {
  Presonus::Surface::SurfaceRootComponent root;
  Presonus::Surface::CascadeHandler handler(root);
  Presonus::UC::NetworkItem item(&root);
  item.setPortableIdentity("cascade-release-item");
  for (auto *argument :
       {static_cast<Presonus::UC::NetworkItem *>(nullptr), &item}) {
    handler.onNetworkItemReleased(argument);
    const bool unchanged = &handler.root() == &root &&
                           handler.items().count() == 0 &&
                           std::string_view(item.portableIdentity().str()) ==
                               "cascade-release-item";
    std::cout << unchanged << '\n';
  }
}
