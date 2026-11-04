#include "presonus/reconstruction200/large02_w06.hpp"
#include "core/portable/corepersistence.h"
#include "presonus/panel/FxPresetComponent.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include <cmath>
#include <cstring>
#include <stdexcept>
namespace {
Core::Portable::Parameter &required(const Core::Portable::Component &component,
                                    int tag) {
  auto *p = component.getParameterByTag(tag);
  if (!p)
    throw std::logic_error("missing preset parameter binding");
  return *p;
}
int integerValue(Core::Portable::Parameter &p) {
  const float v = p.getValue();
  if (!std::isfinite(v) || v < -2147483648.f || v >= 2147483648.f)
    throw std::domain_error("preset integer domain");
  return static_cast<int>(v);
}
} // namespace
namespace presonus::panel {
Core::Portable::Component &ChannelPresetState::selected() const {
  const auto index = mixer.getSelectedChannel();
  if (index >= static_cast<unsigned>(channels.count()) ||
      !channels.at(static_cast<int>(index)))
    throw std::logic_error("missing selected channel binding");
  return *channels.at(static_cast<int>(index));
}
} // namespace presonus::panel
namespace Presonus::Panel {
ChannelPresetComponent::~ChannelPresetComponent() = default;
GeqPresetComponent::~GeqPresetComponent() = default;
ScenesComponent::~ScenesComponent() = default;
bool ChannelPresetComponent::saveUserName() const {
  auto &channel = state.selected();
  auto &source = required(*this, 3);
  auto &destination = required(channel, 2);
  Core::CString256 text;
  source.toString(text.getBuffer(), text.getSize());
  destination.fromString(text, false);
  return true;
}
void ChannelPresetComponent::updatePresetName() const {
  PresetComponent::updatePresetName();
  auto &channel = state.selected();
  auto &destination = required(*this, 3);
  auto &source = required(channel, 2);
  Core::CString256 text;
  source.toString(text.getBuffer(), text.getSize());
  destination.fromString(text, false);
}
bool ChannelPresetComponent::recall(Core::Portable::Attributes &attributes,
                                    bool) {
  auto &channel = state.selected();
  Core::Portable::InputStorage storage(attributes, state.filter);
  storage.setMode("ignoreAltMemory");
  if (!channel.load(storage))
    return false;
  presetRecalled();
  return true;
}
bool ChannelPresetComponent::store() {
  auto &channel = state.selected();
  Core::Portable::Attributes attributes(
      Core::Portable::AttributeAllocator::getDefault());
  Core::Portable::AttributesBuilder builder(attributes);
  Core::Portable::OutputStorage storage(builder, state.filter);
  storage.setMode("ignoreAltMemory");
  channel.save(storage);
  Core::CString256 name, category;
  if (auto *p = getParameterByTag(2))
    p->toString(name.getBuffer(), name.getSize());
  if (auto *p = getParameterByTag(100))
    p->toString(category.getBuffer(), category.getSize());
  doPresetSave(name, category, attributes);
  // Native slot 0x30 dispatches virtual saveUserName after save scheduling.
  saveUserName();
  return true;
}
bool GeqPresetComponent::recall(Core::Portable::Attributes &attributes, bool) {
  const int index = state.selection ? integerValue(*state.selection) : 0;
  if (index < 0 || index >= state.equalizers.count())
    return false;
  auto *equalizer = state.equalizers.at(index);
  if (!equalizer)
    return false;
  Core::Portable::InputStorage storage(attributes);
  storage.setMode("ignoreAltMemory");
  if (!equalizer->load(storage))
    return false;
  presetRecalled();
  return true;
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
bool ScenesComponent::store() {
  const int slot = getSlotNum();
  if (!slot)
    return false;
  Core::CString256 name;
  required(*this, 2).toString(name.getBuffer(), name.getSize());
  auto *cache = getCache();
  const auto filename = cache->buildFileName(static_cast<unsigned>(slot), name,
                                             "", nullptr, true);
  const auto previous = getFileNameForSlot(static_cast<unsigned>(slot));
  if (!previous.isEmpty() && std::strcmp(filename.str(), previous.str()) != 0)
    Core::Portable::FileUtils::deleteFile(previous.str());
  mixer.saveScene(filename, name, true);
  getCache()->cachePreset(name, "", slot);
  presetStored();
  return true;
}
} // namespace Presonus::Panel
namespace Presonus::Panel {
const char *ChannelPresetComponent::getCategory(int slot) {
  // Original app uses a function-static category scratch buffer. This source
  // port reuses the actual cache provider; negative original cache indices are
  // outside the independently bounded domain and rejected here.
  if (slot < 0)
    throw std::out_of_range("negative preset category slot");
  static Core::CString32 category;
  Core::CString64 name;
  category.empty();
  getCache()->getPresetInfo(name, category, slot);
  return category.str();
}
void ChannelPresetComponent::slotChanged(int slot) {
  if (const char *text = getCategory(slot))
    required(*this, 100).fromString(text, false);
}
void ChannelPresetComponent::categoryChanged() {
  if (!state.categoryFollow || !(state.categoryFollow->getValue() > 0.f))
    return;
  Core::CString32 selected;
  required(*this, 100).toString(selected.getBuffer(), selected.getSize());
  for (int i = 0; i < 99; ++i) {
    Core::CString32 candidate(getCategory(i));
    if (candidate == selected.str()) {
      required(*this, 0).setValue(static_cast<float>(i), true);
      return;
    }
  }
}
void ChannelPresetComponent::paramChanged(Core::Portable::Parameter *p,
                                          int message) {
  PresetComponent::paramChanged(p, message);
  const int tag = p->getTag();
  if (message != 2)
    return;
  if (tag == 0)
    slotChanged(integerValue(*p));
  else if (tag == 100)
    categoryChanged();
}
} // namespace Presonus::Panel
