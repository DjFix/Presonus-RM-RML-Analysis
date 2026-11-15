#include "presonus/panel/StormFrontPanelComponent.hpp"
#include <iostream>
using presonus::stormpanel_port::Handle;
struct Unused final : presonus::stormpanel_port::Dependencies {
  void cleanup() override { throw 1; }
  void presetRecalled() override { throw 1; }
  void fatChannelUpdate() override { throw 1; }
  void fatMeterUpdate(Presonus::Mixer::ChannelComponent &) override { throw 1; }
  Handle findGroup(int) override { throw 1; }
  Handle byTag(Handle, int) override { throw 1; }
  void setControl(Handle, int, int) override { throw 1; }
  int count(Handle) override { throw 1; }
  Handle at(Handle, int) override { throw 1; }
  Handle asLED(Handle) override { throw 1; }
  int tag(Handle) override { throw 1; }
  void setBlinkMode(Handle, bool) override { throw 1; }
  void blinkLED(int, std::uint32_t, bool) override { throw 1; }
  Presonus::Panel::MixerLCD *constructLCD(std::size_t) override { throw 1; }
  void addBook(Presonus::Panel::MixerLCD *, std::uint32_t, int) override {
    throw 1;
  }
};
int main() {
  Unused unused;
  Presonus::Panel::StormFrontPanelComponent owner(unused);
  int group;
  static const int markerA = 88, markerB = 99;
  while (std::cin >> group) {
    const int *a = &markerA, *b = &markerB;
    int count = 77;
    owner.getTablesForGroup(group, a, b, count);
    std::cout << count;
    if (group < 0 || group > 2) {
      if (a != &markerA || b != &markerB || count != 77)
        return 4;
    } else {
      for (int i = 0; i < count; ++i)
        std::cout << ' ' << a[i];
      for (int i = 0; i < count; ++i)
        std::cout << ' ' << b[i];
    }
    std::cout << '\n';
  }
}
