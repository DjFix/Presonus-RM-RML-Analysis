#include "presonus/MappingTable.hpp"
#include "presonus/surface_panel/LEDState.hpp"

namespace Presonus {
MappingTable::Item::Item(const char *itemName,
                         Core::Portable::AliasParam *itemAlias)
    : alias(itemAlias), control(nullptr), name(itemName),
      defaultColor(nullptr) {}

void MappingTable::Item::setBlinkMode(const char *mode) {
  if (!control)
    return;
  auto *led = static_cast<Panel::LEDControl *>(control->castTo(1281713219));
  if (!led)
    return;
  struct Mode {
    const char *name;
    int value;
  };
  static constexpr Mode modes[] = {
      {"off", 0}, {"blink", 3}, {"blink-off", 1}, {"blink-on", 2}};
  int value = 0;
  for (const auto &entry : modes) {
    if (std::strcmp(mode ? mode : "", entry.name) == 0) {
      value = entry.value;
      break;
    }
  }
  led->setBlinkMode(static_cast<Panel::LEDControl::BlinkMode>(value));
}

void MappingTable::Item::setInverseMode(bool inverse) {
  if (!control)
    return;
  if (auto *led = static_cast<Panel::LEDControl *>(control->castTo(1281713219)))
    led->setInverseMode(inverse);
}
} // namespace Presonus
