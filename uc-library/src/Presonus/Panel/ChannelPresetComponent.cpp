#include "presonus/panel/ChannelPresetComponent.hpp"
#include "PresetParameterAccess.hpp"
#include "core/portable/corepersistence.h"
#include "presonus/panel/PresetNameCache.hpp"
#include <cstring>
#include <memory>

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
namespace {
// Native table 0x16f964 and its string list at 0x454fa4; expressed using the
// pinned provider's declarations, not copied as ARM-layout structures.
const char *channelCategories[] = {"Drum",   "Perc",  "Guit", "Keys", "Vocal",
                                   "String", "Brass", "Wind", "Other"};
BEGIN_PARAMINFO(channelPresetParameters)
PARAM_LIST_(100, "category", channelCategories, 0, PARAM_PRIVATE,
            "Preset Category", nullptr)
END_PARAMINFO
} // namespace
ChannelPresetComponent::ChannelPresetComponent(
    Presonus::Mixer::MixerComponentBase &mixer)
    : PresetComponent("channel", "My Channels", "channelnum", mixer),
      state{mixer, Core::ConstVector<Core::Portable::Component *>(nullptr, 0),
            nullptr, nullptr} {
  // An owned parameter is transferred into the actual CCL ParamList. Keep
  // ownership local until the vector accepts it, matching existing base-port
  // exception safety rather than leaking on a failed allocation.
  auto parameter =
      std::make_unique<Core::Portable::ListParam>(channelPresetParameters[0]);
  paramList.add(parameter.get());
  parameter.release();
  categoryParameter_ = Core::Portable::core_cast<Core::Portable::ListParam>(
      getParameterByTag(100));
}
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
void ChannelPresetComponent::categoryChanged() { onPresetCategoryChanged(); }
void ChannelPresetComponent::onPresetCategoryChanged() {
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
