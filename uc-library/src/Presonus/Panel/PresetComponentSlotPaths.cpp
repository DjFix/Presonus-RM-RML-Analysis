#include "presonus/panel/PresetComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"

// Slot-to-file lookup is a distinct implementation unit so the native replay
// can observe the existing getCache call boundary without changing fixtures.
namespace Presonus::Panel {
Core::Portable::FileName
PresetComponent::getFileNameForSlot(unsigned int slot) const {
  return getCache()->getFileNameForSlot(slot, true);
}
} // namespace Presonus::Panel
