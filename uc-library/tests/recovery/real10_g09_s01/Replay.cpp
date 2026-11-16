#include "presonus/mixer/DigitalInputComponent.hpp"
#include "presonus/mixer/MixerComponent.hpp"
#include <array>
#include <cxxabi.h>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
static bool recording;
static const void *volatile castObservation;
static std::ostringstream trace;
static std::unordered_map<const void *, int> channelIds, paramIds;
extern "C" Core::Portable::Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(
    const Core::Portable::Component *, int);
extern "C" Core::Portable::Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(
    const Core::Portable::Component *p, int tag) {
  if (recording)
    trace << "G:" << channelIds.at(p) << ':' << tag << ';';
  return __real__ZNK4Core8Portable9Component17getParameterByTagEi(p, tag);
}
extern "C" void
__real__ZN4Core8Portable9Parameter7changedEv(Core::Portable::Parameter *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter7changedEv(Core::Portable::Parameter *p) {
  if (recording)
    trace << "X:" << paramIds.at(p) << ';';
  __real__ZN4Core8Portable9Parameter7changedEv(p);
}
extern "C" void *__real___dynamic_cast(const void *,
                                       const __cxxabiv1::__class_type_info *,
                                       const __cxxabiv1::__class_type_info *,
                                       std::ptrdiff_t);
extern "C" void *__wrap___dynamic_cast(const void *p,
                                       const __cxxabiv1::__class_type_info *s,
                                       const __cxxabiv1::__class_type_info *d,
                                       std::ptrdiff_t hint) {
  if (recording && channelIds.count(p))
    trace << "T:" << channelIds.at(p) << ';';
  return __real___dynamic_cast(p, s, d, hint);
}
struct Watch final : Core::Portable::IParamObserver {
  int count{};
  void *castTo(TypeID t) override {
    return t == IParamObserver::kTypeID ? static_cast<IParamObserver *>(this)
                                        : nullptr;
  }
  void paramChanged(Core::Portable::Parameter *, int) override { ++count; }
};
struct UnusedMixerServices final
    : presonus::mixer_component_port::MixerServices {
  [[noreturn]] static void fail() {
    throw std::logic_error("unexpected Mixer service call");
  }
  void serverParamChanged(Presonus::Mixer::MixerComponent &,
                          Core::Portable::Parameter *, int) override {
    fail();
  }
  Core::Portable::Component &
  parameterComponent(Presonus::Mixer::ChannelComponent &) const override {
    fail();
  }
  Presonus::LinkableComponent *
  linkIdentity(Presonus::Mixer::ChannelComponent *) const override {
    fail();
  }
  const Core::Portable::IStorageFilter *storageFilter(int, bool) override {
    fail();
  }
  void load(const Core::Portable::InputStorage &) override { fail(); }
  void save(Core::Portable::OutputStorage &) override { fail(); }
  bool muteExcluded(const Presonus::Mixer::ChannelComponent &) const override {
    fail();
  }
  Core::Portable::Parameter &
  muteSource(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  Core::Portable::Parameter &
  muteDestination(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  Core::Portable::Parameter &
  selection(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    fail();
  }
  void command(const char *, const char *, int) override { fail(); }
};

int main(int argc, char **argv) {
  const bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  int a, b, c;
  while (std::cin >> a >> b >> c) {
    recording = false;
    trace.str("");
    trace.clear();
    channelIds.clear();
    paramIds.clear();
    std::array<Core::Portable::ParamInfo, 12> infos;
    std::array<Watch, 12> watches;
    std::array<Presonus::Mixer::ChannelComponent *, 12> channels{};
    std::array<Core::Portable::Parameter *, 12> params{};
    std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> objects;
    std::array<Core::Vector<Presonus::Mixer::ChannelComponent *>, 3> groups;
    int sizes[] = {a, b, c};
    for (int group = 0; group < 3; ++group)
      for (int i = 0; i < sizes[group]; ++i) {
        int kind = 1, present;
        if (group == 1)
          std::cin >> kind >> present;
        else
          std::cin >> present;
        const int id = group * 4 + i, tag = group == 0   ? 304
                                            : group == 1 ? 360
                                                         : 340;
        if (!kind) {
          groups[group].add(nullptr);
          continue;
        }
        std::unique_ptr<Presonus::Mixer::ChannelComponent> channel;
        if (kind == 2)
          channel = std::make_unique<Presonus::Mixer::DigitalInputComponent>(
              Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
        else
          channel = std::make_unique<Presonus::Mixer::ChannelComponent>(
              Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
        channels[id] = channel.get();
        channelIds[static_cast<Core::Portable::Component *>(channel.get())] =
            id;
        if (present) {
          infos[id] = PARAM_FLOAT(tag, "notify", 0.f, 1.f, 0.f, .01f, nullptr,
                                  nullptr, 0.f, 0);
          channel->addParameters(&infos[id], 1);
          params[id] = channel->getParameterByTag(tag);
          paramIds[params[id]] = id;
          params[id]->addObserver(&watches[id]);
        }
        groups[group].add(channel.get());
        objects.push_back(std::move(channel));
      }
    presonus::mixer_component_port::MixerState state;
    state.avbListeners = {&groups[0], &groups[1], &groups[2]};
    UnusedMixerServices services;
    Presonus::Mixer::MixerComponent mixer(state, services);
    recording = true;
    if (!provider)
      mixer.onAVBListenerChange();
    else {
      int calls;
      std::cin >> calls;
      for (int i = 0; i < calls; ++i) {
        int code, id;
        std::cin >> code >> id;
        if (code == 0) {
          int tag;
          std::cin >> tag;
          (void)channels[id]->getParameterByTag(tag);
        } else if (code == 1) {
          castObservation =
              dynamic_cast<Presonus::Mixer::DigitalInputComponent *>(
                  channels[id]);
        } else if (code == 2)
          params[id]->changed();
        else
          throw std::logic_error("bad provider code");
      }
    }
    recording = false;
    std::cout << "RESULT " << trace.str() << '|';
    for (int i = 0; i < 12; ++i) {
      std::cout << watches[i].count << ' ';
      if (params[i])
        params[i]->removeObserver(&watches[i]);
    }
    std::cout << '\n';
  }
}
