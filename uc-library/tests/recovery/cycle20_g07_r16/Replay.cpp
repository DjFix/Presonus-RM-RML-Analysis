#include "presonus/panel/LCDComponent.hpp"

#include <cstdlib>
#include <iostream>
#include <memory>

using Presonus::Panel::Book;
using Presonus::Panel::LCDComponent;

namespace {
class Child : public Core::Portable::Component {
public:
  void onIdle() override { ++calls; }
  int calls = 0;
};
} // namespace

int main() {
  LCDComponent component;
  auto *first = new Child;
  auto *second = new Child;
  component.addChild(first);
  component.addChild(second);
  component.onIdle();
  std::cout << first->calls << ' ' << second->calls << '\n';
}
