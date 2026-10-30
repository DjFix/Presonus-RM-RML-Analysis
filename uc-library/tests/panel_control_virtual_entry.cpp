#include "presonus/panel/control.hpp"

// Independent Linux/Itanium test entry, not an original application method.
// Separate TU and no LTO retain the actual native virtual table dispatch.
extern "C" void controlLifecycleEntry(Presonus::Panel::Control *value,
                                      unsigned slot) {
  auto **table = *reinterpret_cast<void ***>(value);
  using Entry = void (*)(Presonus::Panel::Control *);
  reinterpret_cast<Entry>(table[slot])(value);
}
