#include "core/portable/corecomponent.h"
#include "presonus/surface/FatChannelClipboard.hpp"
#include <cstring>
#include <iostream>

namespace {
class Component final : public Core::Portable::Component {
public:
  explicit Component(int &destroyed)
      : Core::Portable::Component("borrowed"), destroyed(destroyed) {}
  ~Component() override { ++destroyed; }
  int &destroyed;
};

struct Derived final : Presonus::Surface::FatChannelClipboard {};
} // namespace

int main() {
  int destroyed = 0;
  {
    Component component(destroyed);
    {
      Presonus::Surface::FatChannelClipboard clipboard;
      auto &roster = clipboard.portableRoster();
      std::cout << clipboard.portableHasOwner() << ' '
                << clipboard.portableHasSource() << ' ' << roster.isEmpty()
                << ' ' << roster.getCapacity() << ' ' << roster.count() << ' '
                << roster.getDelta() << ' ';
      if (!roster.resize(1))
        return 2;
      roster.add(&component);
      std::cout << roster.getCapacity() << ' ' << roster.count() << ' '
                << (roster.at(0) == &component) << ' ';
    }
    std::cout << destroyed << ' '
              << (std::strcmp(component.getName(), "borrowed") == 0) << ' ';
  }
  std::cout << destroyed << '\n';
}
