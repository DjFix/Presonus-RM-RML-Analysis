#include "presonus/panel/PanelComponent.hpp"
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
namespace Presonus::Panel {
class ControlGroup {};
} // namespace Presonus::Panel
struct Boundary : presonus::panel_port::Services {
  int n = 0;
  mutable std::string trace;
  Presonus::Panel::ControlGroup group;
  void event(const char *s, int a = 0, int b = 0) const {
    trace += std::string(s) + ":" + std::to_string(a) + "," +
             std::to_string(b) + ";";
  }
  int groupCount() const override {
    event("groupCount");
    return n;
  }
  const Presonus::Panel::ControlGroup &groupAt(int i) const override {
    event("groupAt", i);
    return group;
  }
  std::uint32_t groupTag(const Presonus::Panel::ControlGroup &) const override {
    return n;
  }
  int controlCount(const Presonus::Panel::ControlGroup &) const override {
    event("controlCount");
    return n;
  }
  void *controlAt(const Presonus::Panel::ControlGroup &, int i) const override {
    event("controlAt", i);
    return i % 2 ? nullptr : (void *)0x202000;
  }
  void controlSlot10(void *, int a, int b) const override {
    event("slot10", a, b);
    if (a || b)
      throw 1;
  }
  void componentSlot38() override { event("slot38"); }
  void *findGroup(int i) override {
    event("findGroup", i);
    return (void *)0x201000;
  }
  void *byTag(void *, int i) override {
    event("byTag", i);
    return n ? (void *)0x202000 : nullptr;
  }
  void *castControlToLed(void *) override {
    event("cast");
    return n > 0 ? (void *)0x202000 : nullptr;
  }
  void setBlinkMode(void *, int i) override { event("blink", i); }
};
int main() {
  Boundary b;
  Presonus::Panel::PanelComponent p(b);
  for (int m = 0; m < 5; ++m)
    for (int n : {-1, 0, 1, 3, 12})
      for (int f : {0, 1}) {
        b.n = n;
        b.trace.clear();
        switch (m) {
        case 0:
          p.detachGroup(b.group);
          break;
        case 1:
          p.detachAll();
          break;
        case 2:
          p.detachSwitches();
          break;
        case 3:
          p.activateAll();
          break;
        case 4:
          p.blinkLed(7, 9, f);
          break;
        }
        std::cout << m << " " << n << " " << f << " " << b.trace << "\n";
      }
}
