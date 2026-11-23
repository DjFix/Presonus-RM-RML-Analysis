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
class ObservedLCD : public LCDComponent {
public:
  void onIdle() override {
    ++calls;
    LCDComponent::onIdle();
  }
  int calls = 0;
};
} // namespace

int main() {
  ObservedLCD component;
  auto *child = new Child;
  component.addChild(child);
  LCDComponent &receiver = component;
  receiver.doIdle();
  std::cout << component.calls << ' ' << child->calls << '\n';
}
