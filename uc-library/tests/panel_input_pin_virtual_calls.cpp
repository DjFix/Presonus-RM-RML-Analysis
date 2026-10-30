#include "presonus/surface_panel/InputPin.hpp"
// Separate non-LTO TU prevents call-site devirtualization; these invoke the
// actual native destructor table entries. This is a native ABI test helper.
extern "C" void inputPinNativeD1(Presonus::Panel::InputPin *pin) {
  auto **slots = *reinterpret_cast<void ***>(pin);
  reinterpret_cast<void (*)(Presonus::Panel::InputPin *)>(slots[0])(pin);
}
extern "C" void inputPinNativeD0(Presonus::Panel::InputPin *pin) {
  auto **slots = *reinterpret_cast<void ***>(pin);
  reinterpret_cast<void (*)(Presonus::Panel::InputPin *)>(slots[1])(pin);
}
