#include "core/portable/corepersistence.h"
#include "presonus/mixer/MixerComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
static std::ostringstream trace;
static bool recording;
static int nested;
static Core::Portable::Attributes *watched;
extern "C" void
__real__ZN4Core8Portable10Attributes9removeAllEv(Core::Portable::Attributes *);
extern "C" void __wrap__ZN4Core8Portable10Attributes9removeAllEv(
    Core::Portable::Attributes *a) {
  if (recording && !nested && a == watched)
    trace << "C;";
  __real__ZN4Core8Portable10Attributes9removeAllEv(a);
}
struct MuteServices final : presonus::mixer_component_port::MixerServices {
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
    return nullptr;
  }
  void load(const Core::Portable::InputStorage &) override {}
  void save(Core::Portable::OutputStorage &storage) override {
    Core::Portable::AttributesWriter writer(storage.getWriter());
    Core::Portable::AttributeValue value;
    value.set(static_cast<Core::int64>(1));
    writer.writeValue("saved", value);
  }
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

struct Param final : Core::Portable::NumericParam {
  int index;
  Param(const Core::Portable::ParamInfo &info, int i)
      : NumericParam(info), index(i) {}
  float getValue() const override {
    if (recording && !nested)
      trace << "G:" << index << ';';
    return NumericParam::getValue();
  }
  void setValue(float v, bool edit = false) override {
    unsigned bits;
    std::memcpy(&bits, &v, 4);
    if (recording && !nested)
      trace << "S:" << index << ':' << bits << ':' << edit << ';';
    NumericParam::setValue(v, edit);
  }
};
struct ParamBox {
  Core::Portable::ParamInfo info;
  Param parameter;
  static Core::Portable::ParamInfo make(float f) {
    return PARAM_FLOAT(1, "mute", -2.f, 2.f, f, .01f, nullptr, nullptr, 0.f, 0);
  }
  ParamBox(float f, int i) : info(make(f)), parameter(info, i) {}
};
struct LoggedMixer final : Presonus::Mixer::MixerComponent {
  using MixerComponent::MixerComponent;
  void
  rememberMutes(Core::Portable::Attributes &a,
                const Presonus::Mixer::MixerComponentBase::Filter &f) override {
    trace << "R:" << f.selector << ';';
    ++nested;
    MixerComponent::rememberMutes(a, f);
    --nested;
  }
  void
  restoreMutes(Core::Portable::Attributes &a,
               const Presonus::Mixer::MixerComponentBase::Filter &f) override {
    trace << "L:" << f.selector << ';';
    ++nested;
    MixerComponent::restoreMutes(a, f);
    --nested;
  }
};
int main(int argc, char **argv) {
  const bool providerMode = argc == 2 && std::string(argv[1]) == "--provider";
  int count, mute, saved;
  while (std::cin >> count >> mute >> saved) {
    recording = false;
    nested = 0;
    trace.str("");
    trace.clear();
    presonus::mixer_component_port::MixerState state;
    if (saved)
      state.panicMutes.set("seed", 1);
    std::vector<std::unique_ptr<ParamBox>> params;
    std::vector<presonus::mixer::ChannelState> channels(count);
    std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> objects;
    for (int i = 0; i < count; ++i) {
      long long raw;
      std::cin >> raw;
      if (raw >= 0) {
        unsigned bits = static_cast<unsigned>(raw);
        float f;
        std::memcpy(&f, &bits, 4);
        params.push_back(std::make_unique<ParamBox>(f, i));
        channels[i].mute = &params.back()->parameter;
      } else
        params.push_back(nullptr);
      objects.push_back(std::make_unique<Presonus::Mixer::ChannelComponent>(
          Presonus::Mixer::ChannelComponent::SourcePortConstruction{},
          channels[i]));
      state.channels.add(objects.back().get());
    }
    MuteServices services;
    LoggedMixer mixer(state, services);
    watched = &state.panicMutes;
    recording = true;
    if (!providerMode) {
      mixer.panicMuteAll(mute);
    } else {
      int calls;
      std::cin >> calls;
      for (int i = 0; i < calls; ++i) {
        int code;
        std::cin >> code;
        if (code == 0) {
          int index;
          std::cin >> index;
          (void)params.at(index)->parameter.getValue();
        } else if (code == 1) {
          int index, edit;
          unsigned bits;
          std::cin >> index >> bits >> edit;
          float f;
          std::memcpy(&f, &bits, 4);
          params.at(index)->parameter.setValue(f, edit);
        } else if (code == 2 || code == 3) {
          int selector;
          std::cin >> selector;
          if (code == 2)
            mixer.rememberMutes(state.panicMutes, {selector});
          else
            mixer.restoreMutes(state.panicMutes, {selector});
        } else if (code == 4)
          state.panicMutes.removeAll();
        else
          throw std::logic_error("bad provider instruction");
      }
    }
    recording = false;
    std::cout << "RESULT " << trace.str() << '|' << !state.panicMutes.isEmpty();
    for (const auto &p : params) {
      if (!p) {
        std::cout << " -1";
        continue;
      }
      float f = p->parameter.Core::Portable::NumericParam::getValue();
      unsigned bits;
      std::memcpy(&bits, &f, 4);
      std::cout << ' ' << bits;
    }
    std::cout << '\n';
  }
}
