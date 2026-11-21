#include "presonus/mixer/AutoFilterGroupManager.hpp"
#include "core/public/corestringbuffer.h"
#include "core/system/coredebug.h"
#include "presonus/mixer/ChannelComponent.hpp"
#include <algorithm>
#include <cctype>
#include <cstring>
#include <new>
#include <stdexcept>
namespace Presonus::Mixer {
AutoFilterGroupManager::~AutoFilterGroupManager() {
  const int count = ownedComponents_.count();
  for (int i = 0; i < count; ++i)
    if (auto *component = ownedComponents_[i])
      delete component;
  ownedComponents_.resize(0);
}

void AutoFilterGroupManager::addUpdateChannel(ChannelComponent *channel) {
  try {
    if (updateChannels_.count() >= updateChannels_.getCapacity() &&
        !updateChannels_.resize(updateChannels_.count() + 1))
      return;
    updateChannels_.add(channel);
  } catch (const std::bad_alloc &) {
    // Pinned CCL uses throwing new; adapt to original failed-resize no-op.
  }
}
namespace {
constexpr int kFirstMember = 646;
constexpr int kEndMember = 677;
constexpr int kIcon = 25;
constexpr int kGroupLabel = 600;
constexpr std::array<const char *, 9> categories{"Drum",  "Perc",  "Guit",
                                                 "Keys",  "Vocal", "String",
                                                 "Brass", "Wind",  "Other"};

bool hasMembers(const Core::Portable::Component &group) {
  for (int tag = kFirstMember; tag != kEndMember; ++tag)
    if (const auto *member = group.getParameterByTag(tag);
        member && member->getValue() > 0)
      return true;
  return false;
}

void appendBounded(Core::CString32 &name, const char *text) {
  std::strncat(name.getBuffer(), text, name.getSize() - 1 - name.length());
}
} // namespace

void AutoFilterGroupManager::updateAutoGroup(ChannelComponent *channel) {
  if (!autoGrouping_ || !channel)
    throw std::logic_error(
        "live channel and borrowed auto-group state required");
  const auto &ordinals = autoGrouping_->channelOrdinals;
  const auto ordinal = std::find_if(
      ordinals.begin(), ordinals.end(),
      [channel](const auto &entry) { return entry.first == channel; });
  if (ordinal == ordinals.end() || ordinal->second < 0 ||
      ordinal->second >= kEndMember - kFirstMember)
    throw std::logic_error("live channel ordinal required");
  const int memberTag = kFirstMember + ordinal->second;
  for (auto *group : autoGrouping_->groups) {
    if (!group)
      continue;
    auto *member = group->getParameterByTag(memberTag);
    if (!(member && member->getValue() > 0))
      continue;
    member->setValue(0, true);
    if (!hasMembers(*group)) {
      Core::DebugPrintf("resetting group %s due to change icon on channel %d\n",
                        group->getName().str(), ordinal->second);
      group->resetToDefaults(false, true, nullptr);
    }
    break;
  }
  auto *icon =
      Core::Portable::StringParam::cast(channel->getParameterByTag(kIcon));
  if (!icon)
    return;
  Core::CString32 name;
  icon->toString(name.getBuffer(), name.getSize());
  Core::DebugPrintf("updating icon %s\n", name.str());
  for (std::size_t i = 0; i < categories.size(); ++i) {
    if (const auto *slash = std::strchr(name.str(), '/'))
      name.subString(name, 0, static_cast<int>(slash - name.str()));
    Core::CString64 category(categories[i]);
    const int length = category.length();
    if (length > 1 && category.str()[length - 1] == 's')
      category.getBuffer()[length - 1] = 0;
    for (auto *c = category.getBuffer(); *c; ++c)
      *c = static_cast<char>(std::tolower(static_cast<unsigned char>(*c)));
    const auto *match = std::strstr(name.str(), category.str());
    if (!match)
      continue;
    Core::DebugPrintf("found category: %s - ", categories[i]);
    Core::CString32 groupName("~");
    char initial[] = {static_cast<char>(std::toupper(
                          static_cast<unsigned char>(name.str()[0]))),
                      0};
    appendBounded(groupName, initial);
    name.subString(name, 1, -1);
    appendBounded(groupName, name.str());
    Core::DebugPrintf("creating new category: %s\n", groupName.str());
    if (auto *group = autoGrouping_->groups[i]) {
      if (auto *label = Core::Portable::StringParam::cast(
              group->getParameterByTag(kGroupLabel)))
        label->fromString(groupName.str(), true);
      if (auto *member = group->getParameterByTag(memberTag))
        member->setValue(1, true);
    }
  }
}

void AutoFilterGroupManager::onIdle() {
  Core::Portable::Component::onIdle();
  if (updateChannels_.isEmpty() || !updateChannels_.first())
    return;
  auto *channel = updateChannels_.first();
  updateChannels_.removeFirst();
  updateAutoGroup(channel);
}
} // namespace Presonus::Mixer
