#include "presonus/surface_panel/LEDState.hpp"
// Separate no-LTO native ABI observer. No manually synthesized deletion event.
extern "C" void ledLifecycleEntry(Presonus::Panel::Control *value,
                                  unsigned slot) {
  auto **table = *reinterpret_cast<void ***>(value);
  using Entry = void (*)(Presonus::Panel::Control *);
  reinterpret_cast<Entry>(table[slot])(value);
}
