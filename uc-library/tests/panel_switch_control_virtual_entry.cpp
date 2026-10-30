#include "presonus/panel/switch_control.hpp"
extern "C" void switchLifecycleEntry(Presonus::Panel::Control *value,
                                     unsigned slot) {
  auto **table = *reinterpret_cast<void ***>(value);
  using Entry = void (*)(Presonus::Panel::Control *);
  reinterpret_cast<Entry>(table[slot])(value);
}
