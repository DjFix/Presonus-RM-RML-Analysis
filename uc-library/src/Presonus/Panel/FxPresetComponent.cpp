#include "presonus/panel/FxPresetComponent.hpp"
#include "PresetParameterAccess.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include <stdexcept>

namespace Presonus::Panel {
FxPresetComponent::FxPresetComponent(
    presonus::panel::PresetApplicationServices &services,
    Core::Portable::Parameter *parameter, FXPresetRecallComponent *const *items,
    int count)
    : preset(std::make_unique<PresetComponent>(services)),
      ownedRecalls(std::make_unique<Core::Vector<FXPresetRecallComponent *>>()),
      recalls(nullptr, 0) {
  if (count < 0 || (count && !items))
    throw std::invalid_argument("invalid FX recall collection");
  for (int i = 0; i < count; ++i)
    if (!ownedRecalls->add(items[i]))
      throw std::bad_alloc();
  recalls = Core::ConstVector<FXPresetRecallComponent *>(
      ownedRecalls->getItems(), ownedRecalls->count());
  observed = parameter;
  if (observed)
    observed->addObserver(preset.get());
}
FxPresetComponent::FxPresetComponent(FrontPanelComponent &front,
                                     Presonus::Mixer::MixerComponentBase &mixer)
    : preset(
          std::make_unique<PresetComponent>("fx", "My Fx", "reverbnum", mixer)),
      ownedRecalls(
          std::make_unique<Core::Vector<FXPresetRecallComponent *>>(0, 5)),
      recalls(nullptr, 0) {
  // The native front-panel Component is mapped explicitly to this existing
  // portable real CCL component; composition is not original ARM inheritance.
  fxParameters = &front.portableState().component;
  auto *parameter = fxParameters->getParameterByTag(13);
  observed = parameter;
  if (observed)
    observed->addObserver(preset.get());
  try {
    preset->bindFxDelegate(
        *this, reinterpret_cast<PresetComponent::Delegate *>(&delegateToken));
  } catch (...) {
    if (observed)
      observed->removeObserver(preset.get());
    throw;
  }
}
FxPresetComponent::~FxPresetComponent() {
  if (observed)
    observed->removeObserver(preset.get());
  ownedRecalls.reset();
  // Executes the canonical PresetComponent destructor and pinned Core cleanup.
  // This provider is not separately admitted as original destructor behavior.
  preset.reset();
}

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
void FxPresetComponent::presetRecalled(const PresetComponent &, int) {
  // RM13731 exact body at0x56d30 consists only of frame setup/return.
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
