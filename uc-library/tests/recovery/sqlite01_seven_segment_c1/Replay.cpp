#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstring>
#include <iostream>
#include <new>

namespace presonus::panel_binding {
struct SevenSegControlAccess {
  static const auto &
  digitBitmaps(const Presonus::Panel::SevenSegControl &value) {
    return value.digitBitmaps_;
  }
};
} // namespace presonus::panel_binding

using Presonus::Panel::Control;
using presonus::panel::ControlAccess;
using Presonus::Panel::SevenSegControl;
using presonus::panel_binding::SevenSegControlAccess;

static void printControl(Control &object) {
  std::cout << ControlAccess::lastLevel(object) << ' '
            << (object.Control::getParameter() != nullptr) << ' '
            << (object.Control::getAltParameter() != nullptr) << ' '
            << (object.Control::getTertiaryParameter() != nullptr) << ' '
            << (ControlAccess::io(object) != nullptr) << ' '
            << ControlAccess::tag(object);
}

int main(int argc, char **argv) {
  if (argc != 3)
    return 1;
  const int seed = std::stoi(argv[1]);
  const int tag = std::stoi(argv[2]);
  using Receiver = SevenSegControl;
  alignas(Receiver) unsigned char storage[sizeof(Receiver)];
  std::memset(storage, seed, sizeof(storage));
  auto *object = new (storage) Receiver;
  if (static_cast<Control *>(object)->castTo(0x4374726c) !=
          static_cast<Control *>(object) ||
      object->convertCharToBmp('8', true) != 255 ||
      object->convertCharToBmp('_', false) != 16)
    return 2;
  printControl(*object);
  for (auto bitmap : SevenSegControlAccess::digitBitmaps(*object))
    std::cout << ' ' << bitmap;
  std::cout << '\n';
  object->~Receiver();

  alignas(Control) unsigned char controlStorage[sizeof(Control)];
  std::memset(controlStorage, seed, sizeof(controlStorage));
  auto *control = new (controlStorage) Control(tag);
  printControl(*control);
  std::cout << '\n';
  control->~Control();

  SevenSegControl tagged(tag);
  if (ControlAccess::tag(tagged) != tag)
    return 4;
}
