#include "presonus/IDAWDialogHandler.hpp"
#include <cstdio>

int main() {
  using Menu = Presonus::IDAWDialogHandler::DialogMenu;
  Core::Vector<Menu *> provider;
  if (!provider.resize(0) || !provider.isEmpty() ||
      provider.getCapacity() != 0 || provider.getDelta() != 5 ||
      provider.getItems() != nullptr)
    return 1;

  for (int receiver = 0; receiver < 8; ++receiver) {
    Menu menu;
    const auto &children = menu.sourcePortChildren();
    for (int call = 0; call < 4; ++call) {
      if (children.count() != provider.count() ||
          children.getCapacity() != provider.getCapacity() ||
          children.getDelta() != provider.getDelta() ||
          children.getItems() != provider.getItems())
        return 2;
      if (call != 3)
        menu.debug();
    }
  }
  std::puts("8 empty DialogMenu receivers, 24 debug calls, empty Core vector");
}
