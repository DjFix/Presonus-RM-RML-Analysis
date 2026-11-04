#include "presonus/panel/ChannelPresetComponent.hpp"
#include "PresetParameterAccess.hpp"
#include "core/portable/corepersistence.h"
#include "presonus/panel/PresetNameCache.hpp"
#include <cstring>

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
