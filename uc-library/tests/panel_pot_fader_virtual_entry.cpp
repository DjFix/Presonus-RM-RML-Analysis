#include "presonus/panel/control.hpp"
extern "C" void potFaderLifecycleEntry(Presonus::Panel::Control *p,
                                       unsigned slot) {
  auto **table = *reinterpret_cast<void ***>(p);
  reinterpret_cast<void (*)(Presonus::Panel::Control *)>(table[slot])(p);
}
