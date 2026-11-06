#include "presonus/StormMuteGroupComponent.hpp"
#include "core/portable/corepersistence.h"
#include "core/system/coredebug.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/PresetNameCache.hpp"
#include "presonus/panel/PresetNameManager.hpp"
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace presonus::storm_mute_port {
bool Timer::executing() const {
  if (production)
    return production->isExecuting();
  if (fixture)
    return fixture->executing();
  throw std::logic_error("unbound mute-group timer");
}
bool Timer::elapsed() const {
  if (production)
    return production->isLongEnoughYet();
  if (fixture)
    return fixture->elapsed();
  throw std::logic_error("unbound mute-group timer");
}
void Timer::end() const {
  if (production) {
    production->endAction();
    return;
  }
  if (fixture) {
    fixture->end();
    return;
  }
  throw std::logic_error("unbound mute-group timer");
}
void Timer::reset() const {
  if (production) {
    production->reset();
    return;
  }
  if (fixture) {
    fixture->reset();
    return;
  }
  throw std::logic_error("unbound mute-group timer");
}
} // namespace presonus::storm_mute_port
namespace Presonus {
using presonus::storm_mute_port::Group;
void StormMuteGroupComponent::setDelegate(Delegate *delegate) {
  state.delegate = delegate;
}
namespace {
void requireInitializedGroups(const presonus::storm_mute_port::State &state) {
  if (state.groups.count() != 8 || !state.allGroup ||
      state.groups.contains(state.allGroup))
    throw std::logic_error("mute-group split-storage correspondence requires "
                           "eight regular groups and a separate all-group");
  for (int i = 0; i < state.groups.count(); ++i)
    if (!state.groups[i])
      throw std::logic_error(
          "null regular mute group outside initialized domain");
}
} // namespace
unsigned int StormMuteGroupComponent::getSwitchTag(unsigned int index) {
  requireInitializedGroups(state);
  return index == static_cast<unsigned int>(state.groups.count()) ? 0u
                                                                  : index + 2u;
}
bool StormMuteGroupComponent::isParamInAnyMuteGroup(
    Core::Portable::Parameter *parameter) {
  requireInitializedGroups(state);
  for (int i = 0; i < state.groups.count(); ++i)
    if (state.groups[i]->state.members.contains(parameter))
      return true;
  return state.allGroup->state.members.contains(parameter);
}
StormMuteGroupComponent::~StormMuteGroupComponent() {
  // Source-port lifecycle: detach borrowed provider observers before
  // destruction.
  for (int i = 0; i < state.groups.count(); ++i)
    if (auto *g = state.groups[i]; g && g->state.alternateStatus)
      g->state.alternateStatus->removeObserver(this);
  if (auto *g = state.allGroup;
      g && g->state.alternateStatus && !state.groups.contains(g))
    g->state.alternateStatus->removeObserver(this);
}
void StormMuteGroupComponent::cleanup() {
  const int count = state.cleanupParameters.count();
  for (int i = 0; i < count; ++i)
    state.cleanupParameters[i]->removeObserver(this);
}
Group *StormMuteGroupComponent::group(unsigned int index) const {
  return index <= INT32_MAX &&
                 index < static_cast<unsigned int>(state.groups.count())
             ? state.groups[static_cast<int>(index)]
             : nullptr;
}
bool StormMuteGroupComponent::recallMutes(unsigned int index, bool value) {
  auto *g = group(index);
  if (g && g->file && (g->busy || g->stored))
    return false;
  Core::DebugPrintf("recallMutes %d %s\n", static_cast<std::int32_t>(index),
                    value ? "true" : "false");
  state.services.refreshSip();
  state.recalling = true;
  if (value)
    state.services.activate(index);
  else
    deactivate(index);
  state.recalling = false;
  return true;
}
void StormMuteGroupComponent::onObserveredParamChanged(
    Core::Portable::Parameter *p, int msg) {
  const char *name = p->getName();
  if (name && std::strstr(name, "status")) {
    refreshGroups();
    return;
  }
  if (msg != 3)
    return;
  if (p->getTag() == 5)
    onCascadeStateChange(p->getValue() > 0.f);
  if (std::strcmp(p->getName() ? p->getName() : "", "mute") == 0 &&
      !state.recalling)
    onMuteChanged(p);
}
void StormMuteGroupComponent::onCascadeStateChange(bool value) {
  Core::Portable::Component *remote = nullptr;
  bool absent = false;
  if (value) {
    if (auto *client = state.services.connectedClient())
      remote = client->findChild(getName());
    else
      absent = true;
  }
  auto bind = [&](Group *g, int localTag, int remoteTag) {
    if (!g)
      return;
    if (g->state.alternateStatus)
      g->state.alternateStatus->removeObserver(this);
    g->state.alternateStatus =
        remote ? remote->getParameterByTag(remoteTag) : nullptr;
    if (g->state.alternateStatus)
      g->state.alternateStatus->addObserver(this);
    g->state.active = absent ? nullptr : getParameterByTag(localTag);
  };
  for (unsigned int i = 0; i < 8; ++i)
    bind(group(i), i + 2, i + 19);
  bind(state.allGroup, 0, 18);
}
void StormMuteGroupComponent::onMuteChanged(Core::Portable::Parameter *p) {
  if (!state.enabled)
    return;
  if (p->getValue() > 0.f) {
    bool member = false;
    for (int i = 0; i < state.groups.count(); ++i)
      if (state.groups[i]->state.members.contains(p)) {
        member = true;
        break;
      }
    if (!member)
      state.loose.add(p);
  } else
    state.loose.remove(p);
  refreshGroups();
}
void StormMuteGroupComponent::groupWasStored(unsigned int index) {
  if (auto *g = group(index))
    for (int i = 0; i < g->state.members.count(); ++i)
      state.loose.remove(g->state.members[i]);
  if (state.observer)
    state.observer->groupDirty(*this, index, false);
}
void StormMuteGroupComponent::refreshGroups() {
  const int count = state.groups.count();
  for (int i = 0; i < count; ++i) {
    auto *g = state.groups[i];
    g->implementation.updateStatus();
    g->implementation.updateActive();
    if (state.observer) {
      const bool dirty = g->implementation.groupDirty();
      if (g->all)
        state.observer->allDirty(*this, dirty);
      else
        state.observer->groupDirty(*this, i, dirty);
    }
  }
}
void StormMuteGroupComponent::notify(const UC::MessageAttributes &message) {
  const char *id = message.getID();
  if (std::strcmp(id ? id : "", "presetMuteGroup") != 0)
    return;
  // ARM caller consumes the low word returned by original Attributes::getInt.
  const auto index =
      static_cast<std::uint32_t>(message.getInt("presetMuteGroupIndex"));
  auto *g = group(index);
  if (!g || !g->file)
    return;
  state.services.muteGroupStored(static_cast<std::int32_t>(index));
  if (state.services.load(*g))
    groupWasStored(index);
}
void StormMuteGroupComponent::onIdle() {
  Core::Portable::Component::onIdle();
  const int count = state.storeTimers.count();
  for (int i = 0; i < count; ++i) {
    const auto timer = state.storeTimers[i];
    if (!timer.present() || !timer.executing() || !timer.elapsed())
      continue;
    timer.end();
    auto *g = group(i);
    if (!g || !g->file)
      continue;
    g->stored = true;
    if (state.services.load(*g))
      groupWasStored(i);
  }
  if (!state.releaseTimer.elapsed())
    return;
  state.releaseTimer.reset();
  for (int i = 0; i < state.delayed.count(); ++i)
    state.delayed[i]->setValue(0.f, true);
  state.delayed.empty();
}
void StormMuteGroupComponent::setAll(bool value) const {
  state.services.refreshSip();
  for (int i = 0; i < state.mixerMutes.count(); ++i)
    if (auto *p = state.mixerMutes[i])
      p->setValue(value ? 1.f : 0.f, true);
  if (!value)
    for (int i = 0; i < state.groups.count(); ++i)
      state.groups[i]->implementation.deactivate();
}
void StormMuteGroupComponent::deactivate(unsigned int index) const {
  auto *g = group(index);
  if (!g)
    return;
  const int count = g->state.members.count();
  for (int i = 0; i < count; ++i) {
    auto *p = g->state.members[i];
    bool other = false;
    for (int j = 0; j < state.groups.count(); ++j)
      if (auto *candidate = state.groups[j];
          candidate != g && candidate->state.members.contains(p)) {
        other = true;
        break;
      }
    if (!other && !state.loose.contains(p))
      p->setValue(0.f, true);
  }
  g->implementation.deactivate();
  g->implementation.updateStatus();
}
} // namespace Presonus

namespace Presonus {
// Initial bytes read from the original ELF static default-name pointer.
// Pointer const qualification remains an intentional source-port declaration.
const char *StormMuteGroupComponent::kDefaultName = "Mute Group";
Core::CStringBuffer<32>
StormMuteGroupComponent::createDefaultName(int index) const {
  Core::CStringBuffer<32> name(kDefaultName);
  // Native ARM addition wraps at 32 bits; avoid signed-overflow undefined
  // behavior for INT_MAX while preserving the canonical Linux int32 result.
  const auto number =
      static_cast<std::int32_t>(static_cast<std::uint32_t>(index) + 1u);
  name.appendFormat(" %i", number);
  return name;
}
} // namespace Presonus

namespace Presonus {
Core::Portable::FileName
StormMuteGroupComponent::getFileName(unsigned int slot) const {
  auto &manager = state.presetNames ? *state.presetNames
                                    : Panel::PresetNameManager::instance();
  if (auto *cache = manager.lookupCache(getName()))
    return cache->buildFileName(slot, "mutegroup", "", nullptr, true);
  return Core::Portable::FileName("");
}
Core::Portable::FileName StormMuteGroupComponent::getSafeListFileName() const {
  // The original caches a process-wide path, including across component
  // objects.
  static Core::Portable::FileName s_path;
  if (s_path.isEmpty()) {
    s_path = getFileName(0);
    Core::Portable::FileName name;
    s_path.getName(name);
    if (const char *match = std::strstr(s_path.str(), name.str())) {
      const auto index = match - s_path.str() - 1;
      if (index >= 0 && index < s_path.length())
        s_path.truncate(static_cast<int>(index));
    }
    Core::Portable::FileUtils::makeDirectory(s_path.str());
    s_path.descend("safeMutes.state");
  }
  return s_path;
}
void StormMuteGroupComponent::storeSafeList() {
  using namespace Core::Portable;
  if (!state.mixer || !state.mixer->saveServices.parameters)
    throw std::logic_error(
        "safe-list requires the actual mixer parameter tree");
  Attributes attributes(AttributeAllocator::getDefault());
  AttributesBuilder builder(attributes, true);
  SafeMuteFilter filter(state);
  OutputStorage storage(builder, &filter);
  if (state.mixer->saveServices.parameters->save(storage))
    ArchiveUtils::saveInBackground(getSafeListFileName().str(), attributes,
                                   nullptr, Archiver::kJSON,
                                   FileStorageContext::kCopy, 0);
}
void StormMuteGroupComponent::onAllMutesChange(bool value) {
  if (state.enabled && value)
    storeSafeList();
}
void StormMuteGroupComponent::startup() {
  using namespace Core::Portable;
  state.loose.empty();
  // Tag zero is required by the initialized native application domain.
  auto *allMutes = getParameterByTag(0);
  if (!allMutes)
    throw std::logic_error("safe-list startup requires tag zero");
  if (!(allMutes->getValue() > 0.f)) {
    state.enabled = true;
    for (int i = 0, count = state.mixerMutes.count(); i < count; ++i)
      state.mixerMutes[i]->changed();
    return;
  }
  if (!state.mixer || !state.mixer->saveServices.parameters)
    throw std::logic_error(
        "safe-list requires the actual mixer parameter tree");
  {
    Attributes attributes(AttributeAllocator::getDefault());
    if (ArchiveUtils::loadFromFile(attributes, getSafeListFileName().str(),
                                   Archiver::kJSON, nullptr, 0, false)) {
      SafeMuteFilter filter(state);
      InputStorage storage(attributes, &filter);
      state.mixer->saveServices.parameters->load(storage);
    }
  } // Destroy attributes before enabling, including during exception unwind.
  state.enabled = true;
}
} // namespace Presonus
