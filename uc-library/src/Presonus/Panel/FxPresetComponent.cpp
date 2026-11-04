#include "presonus/panel/FxPresetComponent.hpp"

namespace Presonus::Panel {
void FxPresetComponent::presetStored(const PresetComponent &, int) {
  auto *const *items = recalls.getItems();
  const int count = recalls.count();
  for (int i = 0; i < count; ++i)
    items[i]->updateFxName();
}
} // namespace Presonus::Panel
