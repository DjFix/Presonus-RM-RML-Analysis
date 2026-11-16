#include "presonus/LinkableComponent.hpp"
#include "presonus/mixer/InputComponent.hpp"
#include "presonus/mixer/TalkbackInputComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>
namespace {
using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
class UnusedLinkBoundary : public Presonus::linkable_port::Boundary {
public:
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    throw std::logic_error("unused query");
  }
  void remove(Presonus::LinkableComponent &) override {
    throw std::logic_error("unused remove");
  }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    throw std::logic_error("unused set");
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    throw std::logic_error("unused master");
  }
};
class PropertyBoundary : public presonus::input_port::Providers {
public:
  presonus::input_port::Property *property;
  presonus::input_port::Property &resolveProperty(const void *p) override {
    if (p != property)
      throw std::logic_error("opaque property mismatch");
    return *property;
  }
  Core::Portable::Parameter *auxPrePost(Core::Portable::Component &c) override {
    return c.getParameterByTag(98);
  }
  void channelSectionChanged(int) override {
    throw std::logic_error("unused section");
  }
  void channelUpdates() override { throw std::logic_error("unused updates"); }
  void meterLevel(int, float) override {
    throw std::logic_error("unused meter");
  }
  void update(int, presonus::input_port::Property &) override {
    throw std::logic_error("unused update");
  }
  void submit(const presonus::input_port::Property &) override {
    throw std::logic_error("unused submit");
  }
};
std::uint32_t bits(float f) {
  std::uint32_t b;
  std::memcpy(&b, &f, 4);
  return b;
}
struct Parameters {
  std::vector<std::unique_ptr<ParamInfo>> infos;
  std::vector<std::unique_ptr<NumericParam>> values;
  NumericParam *add(Core::Portable::Component &c, int tag, float value) {
    auto i = std::make_unique<ParamInfo>();
    i->type = ParamInfo::kFloat;
    i->tag = tag;
    i->minValue = -4.f;
    i->maxValue = 4.f;
    i->defaultValue = value;
    c.addParameters(i.get(), 1);
    auto *result =
        Core::Portable::core_cast<NumericParam>(c.getParameterByTag(tag));
    if (!result)
      throw std::logic_error("actual CCL numeric factory failed");
    result->setValue(value, false);
    infos.push_back(std::move(i));
    return result;
  }
};
} // namespace
int main() {
  int n, talkback, global, self, linkedPan, parity, count;
  float mute;
  float law, base;
  while (std::cin >> n >> talkback >> global >> mute >> self >> linkedPan >>
         parity >> law >> base >> count) {
    Parameters params;
    Core::Portable::Component controls("controls"), globals("globals");
    presonus::input_port::GlobalMuteCache globalCache;
    presonus::input_port::State state;
    state.parameters = &controls;
    state.globalComponent = &globals;
    state.globalCache = &globalCache;
    state.levels[5] = base;
    state.auxiliaryPanLaw = law;
    state.useLinkedAuxPan = linkedPan;
    state.channelIndex = parity;
    state.auxiliaryCachedLevels.assign(8, 0.125f);
    state.auxMuteParameter =
        params.add(controls, 10000, static_cast<float>(mute));
    params.add(globals, 28, static_cast<float>(global));
    UnusedLinkBoundary linkBoundary;
    Presonus::linkable_port::State selfState;
    Presonus::LinkableComponent selfLink(selfState, linkBoundary);
    if (self)
      selfState.partner = &selfLink;
    state.linkable = &selfLink;
    std::unique_ptr<Presonus::Mixer::ChannelComponent> identity;
    if (talkback)
      identity = std::make_unique<Presonus::Mixer::TalkbackInputComponent>(
          Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
    else
      identity = std::make_unique<Presonus::Mixer::ChannelComponent>(
          Presonus::Mixer::ChannelComponent::SourcePortConstruction{});
    state.identity = identity.get();
    std::vector<std::unique_ptr<Core::Portable::Component>> auxiliaries;
    std::vector<std::unique_ptr<Presonus::linkable_port::State>> linkStates;
    std::vector<std::unique_ptr<Presonus::LinkableComponent>> links;
    for (int i = 0; i < n; ++i) {
      float send, pan, width;
      int post, sub, assigned, linked, slave;
      std::cin >> send >> post >> sub >> assigned >> linked >> slave >> pan >>
          width;
      auto aux = std::make_unique<Core::Portable::Component>("aux");
      params.add(*aux, 98, post ? 2.f : 0.f);
      params.add(*aux, 411, static_cast<float>(sub));
      params.add(controls, 0xe0 + i, send);
      params.add(controls, 256 + i, static_cast<float>(assigned));
      if (!(i & 1)) {
        params.add(controls, 0xf0 + i / 2, pan);
        params.add(controls, 0xf8 + i / 2, width);
      }
      auto ls = std::make_unique<Presonus::linkable_port::State>();
      ls->slave = static_cast<std::uint8_t>(slave);
      auto l = std::make_unique<Presonus::LinkableComponent>(*ls, linkBoundary);
      auto *lp = params.add(*aux, 10001, static_cast<float>(linked));
      state.auxiliaryLinks.push_back({lp, l.get()});
      state.auxiliaries.push_back(aux.get());
      auxiliaries.push_back(std::move(aux));
      links.push_back(std::move(l));
      linkStates.push_back(std::move(ls));
    }
    params.add(controls, 19, 0.25f);
    params.add(controls, 20, -0.5f);
    presonus::input_port::Property property;
    property.count = count;
    for (int i = 0; i < count; ++i)
      property.entries[i] = {1000 + i, bits(0.2f)};
    PropertyBoundary boundary;
    boundary.property = &property;
    Presonus::Mixer::InputComponent input(state, boundary);
    input.auxLevelUpdate(
        *reinterpret_cast<Presonus::Dsp::MultiParamProperty *>(&property));
    // Independently observe the actual canonical/pinned providers after replay;
    // these checks do not manufacture expected application results.
    if (selfLink.isLinked() != static_cast<bool>(self) ||
        static_cast<bool>(
            dynamic_cast<Presonus::Mixer::TalkbackInputComponent *>(
                identity.get())) != static_cast<bool>(talkback) ||
        input.isGlobalAuxMute() != static_cast<bool>(global))
      return 3;
    for (int i = 0; i < n; ++i) {
      if (links[i]->isLinkSlave() != static_cast<std::uint8_t>(i & 1) ||
          controls.getParameterByTag(0xe0 + i) == nullptr ||
          auxiliaries[i]->getParameterByTag(411) == nullptr)
        return 4;
    }
    for (float v : state.auxiliaryCachedLevels)
      std::cout << bits(v) << " ";
    std::cout << property.count;
    for (int i = 0; i < property.count; ++i)
      std::cout << " " << property.entries[i].tag << " "
                << property.entries[i].value;
    std::cout << "\n";
  }
}
