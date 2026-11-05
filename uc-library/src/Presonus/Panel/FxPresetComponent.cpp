#include "presonus/panel/FxPresetComponent.hpp"
#include "PresetParameterAccess.hpp"

namespace Presonus::Panel {
Core::Portable::Parameter *FxPresetComponent::getRecallParameter(int index,
                                                                 int tag) {
  auto *child = recalls.at(index);
  return child ? child->getParameterByTag(tag) : nullptr;
}
bool FxPresetComponent::recall(Core::Portable::Attributes &, bool) {
  return false;
}
void FxPresetComponent::presetStored(const PresetComponent &, int) {
  auto *const *items = recalls.getItems();
  const int count = recalls.count();
  for (int i = 0; i < count; ++i)
    items[i]->updateFxName();
}
int FxPresetComponent::getFxIndex() const {
  if (!fxParameters)
    throw std::logic_error("FX parameter component binding required");
  auto *p = fxParameters->getParameterByTag(13);
  return p ? integerValue(*p) : 0;
}
const char *FxPresetComponent::getPresetType() const {
  // The native null provider returns the literal empty type. A bound provider
  // returns a pointer to its type text; source-port storage owns a stable copy.
  return presetTypeBound ? presetType.str() : "";
}
} // namespace Presonus::Panel
