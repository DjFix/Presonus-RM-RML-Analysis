#include "presonus/panel/FxPresetComponent.hpp"
#include "PresetParameterAccess.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cstring>
#include <stdexcept>

namespace Presonus::Panel {
namespace {
// Real CCL observer remains a PresetComponent, preserving tree ownership and
// registration identity while forwarding notifications to its composed owner.
class FxPresetState final : public PresetComponent {
  FxPresetComponent &owner;

public:
  FxPresetState(FxPresetComponent &owner,
                presonus::panel::PresetApplicationServices &services)
      : PresetComponent(services), owner(owner) {}
  FxPresetState(FxPresetComponent &owner, const char *name, const char *display,
                const char *formatter,
                Presonus::Mixer::MixerComponentBase &mixer)
      : PresetComponent(name, display, formatter, mixer), owner(owner) {}
  void paramChanged(Core::Portable::Parameter *p, int message) override {
    owner.paramChanged(p, message);
  }
};
} // namespace

FxPresetComponent::FxPresetComponent(
    presonus::panel::PresetApplicationServices &services,
    Core::Portable::Parameter *parameter, FXPresetRecallComponent *const *items,
    int count)
    : preset(std::make_unique<FxPresetState>(*this, services)),
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
  // Legacy service-backed construction retains its original delegate boundary.
  // The concrete manager binding enables dynamic cache type routing.
  preset->fxDelegate = this;
}
FxPresetComponent::FxPresetComponent(FrontPanelComponent &front,
                                     Presonus::Mixer::MixerComponentBase &mixer)
    : preset(std::make_unique<FxPresetState>(*this, "fx", "My Fx", "reverbnum",
                                             mixer)),
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
  if (preset)
    return currentChild ? currentChild->sourcePortCategory() : "";
  // Legacy borrowed mode has no selected child/tree and retains its explicit
  // copied-type compatibility boundary.
  return presetTypeBound ? presetType.str() : "";
}
} // namespace Presonus::Panel

namespace Presonus::Panel {
void FxPresetComponent::paramChanged(Core::Portable::Parameter *parameter,
                                     int message) {
  if (!preset)
    throw std::logic_error("FX composed preset binding required");
  preset->PresetComponent::paramChanged(parameter, message);
  if (message != 3 || parameter != observed)
    return;
  if (!preset->nameManager)
    throw std::logic_error("concrete preset name manager binding required");
  const int index = integerValue(*observed);
  auto &selection = required(*preset, 0);
  selection.setFormatter(
      Core::FormatterRegistry::find(index <= 1 ? "reverbnum" : "delaynum"));
  if (auto *source = getRecallParameter(integerValue(*observed), 100))
    selection.setValue(source->getValue(), true);
  Core::CString64 oldType(getPresetType());
  // Original invalid indices read the zero-initialized error cell at
  // 0x49452c, store null, then pass address 8 to strcmp. The portable
  // adaptation rejects that faulting domain after the observed state update.
  currentChild = recalls.at(index);
  if (!currentChild)
    throw std::domain_error("native FX selection has no valid child");
  if (std::strcmp(oldType.str(), getPresetType()) != 0) {
    preset->services.ensureNameManager();
    auto lookup = [&](const char *type) {
      return preset->nameManager->lookupCache(type);
    };
    preset->registerCache(lookup(oldType));
    preset->services.ensureNameManager();
    preset->registerCache(lookup(getPresetType()));
  }
  preset->updatePresetName();
  preset->updateEditName();
}
} // namespace Presonus::Panel
