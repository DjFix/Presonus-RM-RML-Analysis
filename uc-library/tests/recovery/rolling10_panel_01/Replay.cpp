#include "presonus/panel/PanelComponent.hpp"
#include <cstdio>
#include <stdexcept>
struct Boundary final : presonus::panel_port::Services {
  int calls = 0;
  int groupCount() const override { throw 1; }
  const Presonus::Panel::ControlGroup &groupAt(int) const override { throw 1; }
  std::uint32_t groupTag(const Presonus::Panel::ControlGroup &) const override {
    throw 1;
  }
  int controlCount(const Presonus::Panel::ControlGroup &) const override {
    throw 1;
  }
  void *controlAt(const Presonus::Panel::ControlGroup &, int) const override {
    throw 1;
  }
  void controlSlot10(void *, int, int) const override { throw 1; }
  void componentSlot38() override { ++calls; }
  void *findGroup(int) override { throw 1; }
  void *byTag(void *, int) override { throw 1; }
  void *castControlToLed(void *) override { throw 1; }
  void setBlinkMode(void *, int) override { throw 1; }
};
int main() {
  Boundary b;
  Presonus::Panel::PanelComponent panel(b);
  for (int i = 0; i < 8; ++i) {
    panel.portableState().active = (i & 1);
    panel.start();
    std::printf("%d %d %d\n", i, b.calls, panel.portableState().active);
  }
}
