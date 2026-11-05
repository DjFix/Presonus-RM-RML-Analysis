#include "presonus/panel/PresetComponent.hpp"
#include "core/portable/corefile.h"
#include "core/portable/corepersistence.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FxPresetComponent.hpp"
#include <cstring>
#include <memory>
#include <stdexcept>

namespace Presonus::Panel {
PresetComponent::PresetComponent(
    presonus::panel::PresetApplicationServices &services)
    : services(services) {}

namespace {
presonus::panel::PresetApplicationServices &
requiredServices(Presonus::Mixer::MixerComponentBase &mixer) {
  if (!mixer.presetApplicationServices)
    throw std::logic_error("preset application services binding required");
  return *mixer.presetApplicationServices;
}
BEGIN_PARAMINFO(presetParameters)
PARAM_INT_(0, "slot_num", 0, 98, 0, "", "", 0, 0, "Slot Number", nullptr),
    PARAM_STRING_(1, "slot_name", 0, "Slot Name", nullptr),
    PARAM_STRING_(2, "loaded_name", 0, "Editable Name", nullptr),
    PARAM_STRING_(3, "user_name", 0, "User Name", nullptr) END_PARAMINFO
} // namespace
PresetComponent::PresetComponent(const char *name, const char *display,
                                 const char *formatterName,
                                 Presonus::Mixer::MixerComponentBase &mixer)
    : Core::Portable::Component(name), services(requiredServices(mixer)),
      displayName(display), delegates(0, 5) {
  // App-side ownership guard: upstream ParamList::add(ParamInfo) creates a raw
  // parameter before vector growth, and leaks it if host allocation throws.
  // Use actual CCL types/ownership while making that transfer exception safe.
  for (const auto &info : presetParameters) {
    std::unique_ptr<Core::Portable::Parameter> parameter;
    if (info.type == Core::Portable::ParamInfo::kString)
      parameter = std::make_unique<Core::Portable::StringParam>(info);
    else
      parameter = std::make_unique<Core::Portable::NumericParam>(info);
    paramList.add(parameter.get());
    parameter.release();
  }
  if (auto *slot = getParameterByTag(0))
    slot->setFormatter(Core::FormatterRegistry::find(formatterName));
  if (auto *parameter = getParameterByTag(2))
    if (auto *text =
            Core::Portable::core_cast<Core::Portable::StringParam>(parameter)) {
      text->setDefaultText(displayName);
      text->resetValue(false);
    }
}

void PresetComponent::paramChanged(Core::Portable::Parameter *parameter,
                                   int message) {
  if (message == 2) {
    if (parameter->getTag() == 0)
      services.updateSelection(*this);
    else if (parameter->getTag() == 1)
      updateEditName();
  }
  Core::Portable::Component::paramChanged(parameter, message);
}

void PresetComponent::updatePresetName() const {
  auto *name = getParameterByTag(1);
  if (!name || !services.hasSelectedSlotParameter(*this))
    return;
  Core::CString64 presetName;
  Core::CString32 category;
  services.ensureNameManager();
  const int slot = services.selectedSlot(*this);
  const char *folder = services.presetFolder(*this);
  services.presetInfo(presetName, category, slot, folder);
  name->fromString(presetName, false);
  if (auto *categoryParameter = getParameterByTag(100))
    categoryParameter->fromString(category, false);
}

void PresetComponent::presetStored() const {
  // Original loop snapshots both backing array and count before callbacks.
  auto *const *items = delegates.getItems();
  const int count = delegates.count();
  for (int i = 0; i < count; ++i)
    if (auto *delegate = items[i])
      notifyDelegate(delegate, services.selectedSlot(*this), true);
}

PresetNameCache *PresetComponent::getCache() const {
  services.ensureNameManager();
  return services.lookupCache(services.presetFolder(*this));
}

bool PresetComponent::isSlotEmpty(unsigned int slot) const {
  const auto fileName = getFileNameForSlot(slot);
  return !fileName.isEmpty() &&
         !Core::Portable::FileUtils::fileExists(fileName);
}

void PresetComponent::updateEditName() const {
  auto *edit = getParameterByTag(2);
  auto *name = getParameterByTag(1);
  if (!name || !edit)
    return;
  Core::CString128 text;
  name->toString(text.getBuffer(), text.getSize());
  if (std::strstr(text, services.emptyNameMarker()))
    edit->resetValue(false);
  else
    edit->fromString(text, false);
}

bool PresetComponent::getCurrentPresetName(
    Core::CStringBuffer<128> &name) const {
  if (auto *parameter = getParameterByTag(1)) {
    parameter->toString(name.getBuffer(), name.getSize());
    return true;
  }
  name = "error";
  return false;
}

int PresetComponent::recall() {
  const int slot = services.selectedSlot(*this);
  if (services.slotEmpty(*this, static_cast<unsigned>(slot)))
    return 0;
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  Core::CString256 fileName;
  services.slotFileName(fileName, *this, static_cast<unsigned>(slot));
  if (!Core::Portable::ArchiveUtils::loadFromFile(
          attributes, fileName,
          static_cast<Core::Portable::Archiver::Format>(0), nullptr, 0, false))
    return 0;
  return services.recallAttributes(*this, attributes, true);
}

void PresetComponent::removeDelegate(Delegate *delegate) {
  delegates.remove(delegate);
}

void PresetComponent::presetRecalled() const {
  updateEditName();
  auto *const *items = delegates.getItems();
  const int count = delegates.count();
  for (int i = 0; i < count; ++i)
    if (auto *delegate = items[i])
      notifyDelegate(delegate, services.selectedSlot(*this), false);
}

void PresetComponent::bindFxDelegate(FxPresetComponent &fx,
                                     Delegate *identity) {
  if (fxDelegate || !identity)
    throw std::logic_error("invalid composed FX delegate binding");
  addDelegate(identity);
  fxDelegate = &fx;
  fxDelegateIdentity = identity;
}
void PresetComponent::notifyDelegate(Delegate *delegate, int slot,
                                     bool stored) const {
  if (delegate == fxDelegateIdentity && fxDelegate) {
    if (stored)
      fxDelegate->presetStored(*this, slot);
    else
      fxDelegate->presetRecalled(*this, slot);
    return;
  }
  services.notifyDelegate(delegate, *this, slot, stored);
}

void PresetComponent::addDelegate(Delegate *delegate) {
  delegates.add(delegate);
}
} // namespace Presonus::Panel

#include "presonus/panel/PresetNameCache.hpp"
#include <cmath>
#include <memory>
#include <stdexcept>
namespace Presonus::Panel {
PresetComponent::~PresetComponent() {
  // Native base ensures the manager and looks up the cache before detaching
  // its observer, then destroys its delegate vector and Core Component.
  services.ensureNameManager();
  auto *cache = services.lookupCache(services.presetFolder(*this));
  if (cache && cacheObserver)
    cache->sourcePortRemoveObserver(cacheObserver);
}
void PresetComponent::sourcePortObserveCache(
    PresetNameCache::Delegate *observer) {
  if (cacheObserver)
    getCache()->sourcePortRemoveObserver(cacheObserver);
  cacheObserver = observer;
  if (cacheObserver)
    getCache()->addObserver(cacheObserver);
}
int PresetComponent::getSlotNum() const {
  auto *selection = getParameterByTag(0);
  if (!selection)
    throw std::logic_error("preset slot parameter required");
  const float value = selection->getValue();
  if (!std::isfinite(value) || value < -2147483648.f || value >= 2147483648.f)
    throw std::domain_error("preset slot integer domain");
  const int slot = static_cast<int>(value);
  // Existing callback-based source ports must bind the same selected state.
  if (services.selectedSlot(*this) != slot)
    throw std::logic_error("inconsistent preset slot binding");
  return slot;
}
void PresetComponent::cacheUpdated(PresetNameCache &, int slot,
                                   const char *name, const char *category) {
  if (slot != getSlotNum())
    return;
  auto *parameter = getParameterByTag(1);
  if (!parameter)
    throw std::logic_error("preset name parameter required");
  parameter->fromString(name, false);
  if (auto *p = getParameterByTag(100))
    p->fromString(category, false);
  updateEditName();
}
void PresetComponent::doPresetSave(
    const char *name, const char *category,
    const Core::Portable::Attributes &attributes) const {
  const int slot = getSlotNum();
  auto *cache = getCache();
  const auto filename = cache->buildFileName(static_cast<unsigned>(slot), name,
                                             category, nullptr, true);
  const auto previous = getFileNameForSlot(static_cast<unsigned>(slot));
  if (!previous.isEmpty() && std::strcmp(filename.str(), previous.str()) != 0)
    Core::Portable::FileUtils::deleteFile(previous.str());
  std::unique_ptr<Core::Portable::FileIOCompletionHandler> handler(
      createStorageHandler());
  if (Core::Portable::ArchiveUtils::saveInBackground(filename.str(), attributes,
                                                     handler.get()))
    handler.release();
  // Original caller updates cache and delegates even when scheduling fails.
  getCache()->cachePreset(name, category, slot);
  presetStored();
}
} // namespace Presonus::Panel

namespace Presonus::Panel {
class PresetComponent::StorageCompletionHandler final
    : public Core::Portable::FileIOCompletionHandler {
  const PresetComponent &owner;

public:
  explicit StorageCompletionHandler(const PresetComponent &owner)
      : owner(owner) {}
  void onSaveFileCompleted(const char *) override;
};
void PresetComponent::StorageCompletionHandler::onSaveFileCompleted(
    const char *) {
  owner.presetStored();
}
Core::Portable::FileIOCompletionHandler *
PresetComponent::createStorageHandler() const {
  return new StorageCompletionHandler(*this);
}
} // namespace Presonus::Panel
