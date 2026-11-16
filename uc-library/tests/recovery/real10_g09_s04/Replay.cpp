#include "core/system/coredebug.h"
#include "presonus/mixer/MixerComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <vector>
static std::ostringstream trace;
static bool recording;
static int nested;
static std::array<Core::Portable::Parameter *, 3> paramIds{};
static int id(Core::Portable::Parameter *p) {
  for (int i = 0; i < 3; ++i)
    if (paramIds[i] == p)
      return i + 1;
  throw std::logic_error("unknown parameter");
}
extern "C" void
__real__ZN4Core8Portable9Parameter7changedEv(Core::Portable::Parameter *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter7changedEv(Core::Portable::Parameter *p) {
  if (recording && !nested)
    trace << "X:" << id(p) << ';';
  __real__ZN4Core8Portable9Parameter7changedEv(p);
}
extern "C" void __real__ZN4Core11DebugPrintfEPKcz(const char *, ...);
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *text, ...) {
  if (recording)
    trace << "D;";
  __real__ZN4Core11DebugPrintfEPKcz("%s", text);
}
struct Param final : Core::Portable::NumericParam {
  int index;
  int notices{};
  Param(const Core::Portable::ParamInfo &i, int n)
      : NumericParam(i), index(n) {}
  void setValue(float v, bool edit = false) override {
    unsigned bits;
    std::memcpy(&bits, &v, 4);
    if (recording && !nested)
      trace << "S:" << index << ':' << bits << ':' << edit << ';';
    ++nested;
    NumericParam::setValue(v, edit);
    --nested;
  }
};
struct Watch final : Core::Portable::IParamObserver {
  void *castTo(TypeID type) override {
    return type == Core::Portable::IParamObserver::kTypeID
               ? static_cast<Core::Portable::IParamObserver *>(this)
               : nullptr;
  }
  int count{};
  void paramChanged(Core::Portable::Parameter *, int) override { ++count; }
};
struct Observer final
    : presonus::mixer_component_port::MixerState::SelectionObserver {
  int index;
  int count{};
  explicit Observer(int i) : index(i) {}
  void selectionChanged() override {
    ++count;
    if (recording)
      trace << "O:" << index << ';';
  }
};
struct Boundary final : Presonus::linkable_port::Boundary {
  [[noreturn]] static void fail() {
    throw std::logic_error("unexpected link mutation");
  }
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    fail();
  }
  void remove(Presonus::LinkableComponent &) override { fail(); }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    fail();
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    fail();
  }
};
struct SelectionServices final : presonus::mixer_component_port::MixerServices {
  std::vector<Presonus::Mixer::ChannelComponent *> channels;
  std::vector<Core::Portable::Parameter *> parameters;
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
  selection(Presonus::Mixer::ChannelComponent &channel) override {
    for (std::size_t i = 0; i < channels.size(); ++i)
      if (channels[i] == &channel)
        return *parameters[i];
    fail();
  }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    fail();
  }
  void command(const char *, const char *, int) override { fail(); }
};
int main(int argc, char **argv) {
  const bool providerMode = argc == 2 && std::string(argv[1]) == "--provider";
  int count, partner, slave, guard, selected, dirty, observers;
  while (std::cin >> count >> partner >> slave >> guard >> selected >> dirty >>
         observers) {
    recording = false;
    nested = 0;
    trace.str("");
    trace.clear();
    presonus::mixer_component_port::MixerState state;
    SelectionServices services;
    Boundary boundary;
    std::array<Presonus::linkable_port::State, 4> linkStates;
    std::vector<std::unique_ptr<Presonus::LinkableComponent>> links;
    std::vector<std::unique_ptr<Presonus::Mixer::ChannelComponent>> channels;
    Core::Portable::ParamInfo info = PARAM_FLOAT(
        1, "selected", 0.f, 1.f, 1.f, .01f, nullptr, nullptr, 0.f, 0);
    std::array<std::unique_ptr<Param>, 3> parameters;
    std::array<Watch, 3> watches;
    for (int i = 0; i < 4; ++i)
      links.push_back(std::make_unique<Presonus::LinkableComponent>(
          linkStates[i], boundary));
    for (int i = 0; i < 3; ++i) {
      channels.push_back(std::make_unique<Presonus::Mixer::ChannelComponent>(
          Presonus::Mixer::ChannelComponent::SourcePortConstruction{}));
      parameters[i] = std::make_unique<Param>(info, i + 1);
      paramIds[i] = parameters[i].get();
      parameters[i]->addObserver(&watches[i]);
      services.channels.push_back(channels[i].get());
      services.parameters.push_back(parameters[i].get());
      state.channelLinks.add(
          {channels[i].get(), links[i].get(), &linkStates[i]});
      if (i < count)
        state.channels.add(channels[i].get());
    }
    linkStates[0].slave = slave;
    linkStates[0].partner = partner ? links[partner - 1].get() : nullptr;
    state.selectedChannel = channels[2].get();
    state.cascadeSelected = selected;
    state.cascadeDirty = dirty;
    state.selectionGuard = guard;
    Observer first(0), second(1);
    if (observers) {
      state.selectionObservers.add(&first);
      state.selectionObservers.add(&second);
    }
    Presonus::Mixer::MixerComponent mixer(state, services);
    recording = true;
    if (!providerMode)
      mixer.doSelect(channels[0].get());
    else {
      int calls;
      std::cin >> calls;
      for (int i = 0; i < calls; ++i) {
        int code;
        std::cin >> code;
        if (code == 0)
          Core::DebugPrintf("MixerComponent::doSelect...\n");
        else if (code == 1) {
          int index, edit;
          unsigned bits;
          std::cin >> index >> bits >> edit;
          float f;
          std::memcpy(&f, &bits, 4);
          parameters[index - 1]->setValue(f, edit);
        } else if (code == 2) {
          int index;
          std::cin >> index;
          parameters[index - 1]->changed();
        } else if (code == 3) {
          int index;
          std::cin >> index;
          (index ? second : first).selectionChanged();
        } else
          throw std::logic_error("bad provider instruction");
      }
    }
    recording = false;
    int selectedIndex = 0;
    for (int i = 0; i < 3; ++i)
      if (state.selectedChannel == channels[i].get())
        selectedIndex = i + 1;
    std::cout << "RESULT " << trace.str() << '|' << selectedIndex << ' '
              << state.cascadeSelected << ' ' << state.cascadeDirty << '|';
    for (int i = 0; i < 3; ++i) {
      float f = parameters[i]->Core::Portable::NumericParam::getValue();
      unsigned bits;
      std::memcpy(&bits, &f, 4);
      std::cout << bits << ' ' << watches[i].count << ' ';
      parameters[i]->removeObserver(&watches[i]);
    }
    std::cout << first.count << ' ' << second.count << '\n';
  }
}
