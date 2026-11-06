#include "presonus/mixer/SceneFilter.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/mixer/CompressorComponent.hpp"
#include "presonus/mixer/EQComponent.hpp"
#include "presonus/mixer/FXBusComponent.hpp"
#include "presonus/mixer/FXComponent.hpp"
#include "presonus/mixer/FilterGroupComponent.hpp"
#include "presonus/mixer/GEQComponent.hpp"
#include "presonus/mixer/GateComponent.hpp"
#include "presonus/mixer/HPFilterComponent.hpp"
#include "presonus/mixer/LPFilterComponent.hpp"
#include "presonus/mixer/LimiterComponent.hpp"
#include "presonus/mixer/MasterSectionComponent.hpp"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/MonoBusComponent.hpp"
#include "presonus/mixer/NetworkSelectComponent.hpp"
#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/mixer/StereoLineComponent.hpp"
#include "presonus/mixer/TalkbackInputComponent.hpp"
#include <cstring>
#include <stdexcept>
namespace Presonus::Mixer {
using namespace Core::Portable;
SceneFilter::SceneFilter(MixerComponentBase &mixer) : mixer_(mixer) {
  refresh();
}
SceneFilter::SceneFilter(const SceneFilter &other) : mixer_(other.mixer_) {
  // Native copy resets enable and parameter caches; refresh discards old mask.
  refresh();
}
void SceneFilter::refresh() {
  mask_ = 0;
  if (!mixer_.sceneSettings)
    return;
  if (!cached_[0])
    for (unsigned i = 0; i != cached_.size(); ++i)
      cached_[i] = mixer_.sceneSettings->getParameterByTag(7 + i);
  constexpr unsigned bits[] = {6, 7, 2, 3, 0, 4, 1, 5, 8, 9};
  for (unsigned i = 0; i != cached_.size(); ++i) {
    // Native dereferences every pointer. Explicitly reject incomplete provider
    // bindings rather than manufacturing behavior outside its defined domain.
    if (!cached_[i])
      throw std::logic_error("SceneFilter requires settings tags 7..16");
    if (cached_[i]->getValue() > 0.f)
      mask_ |= 1u << bits[i];
  }
}
bool SceneFilter::shouldLoad(int type, const char *, void *object) const {
  if (!object)
    return true;
  if (type == Component::kTypeID) {
    auto *c = static_cast<Component *>(object);
    if (core_cast<EQComponent>(c) || core_cast<CompressorComponent>(c) ||
        core_cast<GateComponent>(c) || core_cast<LimiterComponent>(c) ||
        core_cast<HPFilterComponent>(c) || core_cast<LPFilterComponent>(c))
      return bit(1);
    if (core_cast<GEQComponent>(c))
      return bit(5);
    if (core_cast<FXComponent>(c))
      return bit(7);
    if (core_cast<FilterGroupComponent>(c))
      return bit(9);
    if (c == mixer_.sceneSettings)
      return false;
    return core_cast<PermissionsComponent>(c) == nullptr;
  }
  if (type != Parameter::kTypeID)
    return true;
  auto *p = static_cast<Parameter *>(object);
  auto *c = core_cast<Component>(p->getController());
  if (!c)
    return true;
  const int tag = p->getTag();
  if (core_cast<ChannelComponent>(c)) {
    if (tag <= 237) {
      if (tag >= 224)
        return bit(2);
      if (tag == 18)
        return bit(6);
      if (tag > 18) {
        if (tag == 25)
          return bit(8);
        if (tag <= 21 || tag >= 218)
          return bit(0);
        return true;
      }
      if (tag == 2)
        return bit(8);
      if (tag <= 1)
        return tag < 0;
      if (tag == 14)
        return !mixer_.sceneRecallBlocksTag14 && bit(0);
      if (tag != 17)
        return true;
      // One authoritative existing collection and live channel level pointer.
      // Null entries are outside native's dereferenceable collection domain.
      for (int i = 0; mixer_.sceneChannels && i < mixer_.sceneChannels->count();
           ++i) {
        auto *channel = mixer_.sceneChannels->at(i);
        if (!channel)
          throw std::logic_error("SceneFilter requires live input channels");
        if (channel->portableState().level != p)
          continue;
        if (core_cast<MonoBusComponent>(channel) ||
            core_cast<FXBusComponent>(channel) ||
            core_cast<StereoLineComponent>(channel) ||
            core_cast<TalkbackInputComponent>(channel))
          return enabled_ ? bit(4) : bit(3);
        return bit(3);
      }
      return true;
    }
    if (tag == 307)
      return false;
    if (tag < 307) {
      if (tag >= 272)
        return tag >= 300 && tag <= 303 ? bit(2) : true;
      if (tag < 256)
        return tag >= 240 && tag <= 246 ? bit(2) : true;
      return core_cast<TalkbackInputComponent>(c) ? bit(2) : bit(6);
    }
    if (tag >= 320) {
      if (tag == 340)
        return bit(0);
      return tag == 410 ? bit(2) : true;
    }
    if (tag >= 316)
      return bit(6);
    if (tag == 309)
      return bit(0);
    return tag == 314 ? bit(4) : true;
  }
  if (core_cast<MasterSectionComponent>(c)) {
    // Preserve unsigned subtraction/range and literal mask from native code.
    const auto shift = static_cast<unsigned>(tag) - 12u;
    if (shift > 28)
      return true;
    const auto flag = 1u << shift;
    if (flag & 0x03fe03c1u)
      return bit(0);
    if (flag & 0x1c000000u)
      return enabled_ && bit(4);
  }
  return true;
}
bool SceneFilter::shouldSave(int type, const char *, void *object) const {
  if (!object)
    return true;
  if (type == Component::kTypeID) {
    auto *c = static_cast<Component *>(object);
    if (c == mixer_.sceneSettings || core_cast<NetworkSelectComponent>(c) ||
        core_cast<PermissionsComponent>(c))
      return false;
    if (!std::strcmp(c->getName(), "mixscene") ||
        !std::strcmp(c->getName(), "mutegroup"))
      return false;
    if (auto *group = core_cast<FilterGroupComponent>(c))
      return group->isConfigured();
    return true;
  }
  if (type == Parameter::kTypeID) {
    auto *p = static_cast<Parameter *>(object);
    const int tag = p->getTag();
    auto *c = core_cast<Component>(p->getController());
    if (c && (tag == 0 || tag == 1 || tag == 307) &&
        core_cast<ChannelComponent>(c))
      return false;
  }
  return true;
}
} // namespace Presonus::Mixer
