#include "presonus/panel/PresetComponent.hpp"
#include "core/portable/corepersistence.h"
#include <cstring>

namespace Presonus::Panel {
PresetComponent::PresetComponent(
    presonus::panel::PresetApplicationServices &services)
    : services(services) {}

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
      services.notifyDelegate(delegate, *this, services.selectedSlot(*this),
                              true);
}

PresetNameCache *PresetComponent::getCache() const {
  services.ensureNameManager();
  return services.lookupCache(services.presetFolder(*this));
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
      services.notifyDelegate(delegate, *this, services.selectedSlot(*this),
                              false);
}

void PresetComponent::addDelegate(Delegate *delegate) {
  delegates.add(delegate);
}
} // namespace Presonus::Panel
