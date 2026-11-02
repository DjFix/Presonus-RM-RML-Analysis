#include "presonus/mixer/ChannelComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <vector>

namespace {
using namespace Core::Portable;
using Presonus::Mixer::ChannelComponent;
std::vector<std::uint32_t> trace;
float fromBits(std::uint32_t v) {
  float f;
  std::memcpy(&f, &v, 4);
  return f;
}
std::uint32_t bits(float f) {
  std::uint32_t v;
  std::memcpy(&v, &f, 4);
  return v;
}
struct ObservedParam : NumericParam {
  int id;
  float normalized{};
  ObservedParam(const ParamInfo &info, int id) : NumericParam(info), id(id) {}
  float getValue() const override {
    trace.push_back(100 + id);
    return NumericParam::getValue();
  }
  float getNormalized() const override {
    trace.push_back(200 + id);
    return normalized;
  }
  void setValue(float v, bool edit) override {
    trace.push_back(300 + id);
    trace.push_back(bits(v));
    trace.push_back(edit);
    NumericParam::setValue(v, edit);
  }
};
struct Child : Component {
  int id;
  Child(const char *name, int id) : Component(name), id(id) {}
  void resetToDefaults(bool storableOnly, bool edit,
                       const IStorageFilter *filter) override {
    trace.push_back(500 + id);
    trace.push_back(storableOnly);
    trace.push_back(edit);
    Component::resetToDefaults(storableOnly, edit, filter);
  }
};
struct Children : Component {
  Component *findChild(const char *name) const override {
    trace.push_back(std::strcmp(name, "comp") == 0   ? 400
                    : std::strcmp(name, "gate") == 0 ? 401
                                                     : 402);
    return Component::findChild(name);
  }
};
struct Services : presonus::mixer::ChannelApplicationServices {
  bool linked{}, mutateActive{};
  ChannelComponent *pair{};
  bool isLinked(const ChannelComponent &) const override {
    trace.push_back(1);
    return linked;
  }
  void removeLink(ChannelComponent &c) override {
    trace.push_back(2);
    linked = false;
    if (mutateActive)
      c.portableState().active = !c.portableState().active;
  }
  ChannelComponent *linkablePair(ChannelComponent &) override {
    trace.push_back(3);
    return pair;
  }
  void faderLocateDirty(ChannelComponent &) override { trace.push_back(4); }
  void coefficientsChanged(ChannelComponent &, bool solo) override {
    trace.push_back(solo ? 6 : 5);
  }
};
struct Channel : ChannelComponent {
  int mutateUpdate{};
  using ChannelComponent::ChannelComponent;
  void levelUpdate() override {
    trace.push_back(7);
    if (mutateUpdate)
      portableState().updates[1] = mutateUpdate == 1;
  }
  void soloCoeffUpdate() override { trace.push_back(8); }
};
} // namespace
int main() {
  std::vector<std::uint32_t> in;
  std::uint32_t word;
  while (std::cin >> word)
    in.push_back(word);
  if (in.size() != 52) {
    std::cerr << "Expected 52 input words, got " << in.size() << '\n';
    return 2;
  }
  const auto mask = in[1];
  std::array<ParamInfo, 14> info{};
  std::array<std::unique_ptr<ObservedParam>, 14> params;
  Component globals, solos;
  for (int i = 0; i < 14; ++i) {
    info[i] = ParamInfo PARAM_FLOAT(i, "test", -1000000.f, 1000000.f, 0.f,
                                    0.001f, nullptr, nullptr, 0.f, 0);
    if (mask & (1u << i)) {
      params[i] = std::make_unique<ObservedParam>(info[i], i);
      params[i]->setValue(fromBits(in[2 + i]), false);
    }
  }
  const int tags[] = {45, 48, 47, 46};
  // Components own added parameters; retain only borrowed pointers there.
  std::array<ParamInfo, 4> globalInfo{};
  for (int i = 10; i < 14; ++i)
    if (params[i]) {
      globalInfo[i - 10] = info[i];
      globalInfo[i - 10].tag = tags[i - 10];
      // Use real CCL lookup list with independent actual NumericParams.
      globals.addParameters(&globalInfo[i - 10], 1);
      globals.getParameterByTag(tags[i - 10])
          ->setValue(fromBits(in[2 + i]), false);
    }
  ParamInfo soloInfo = info[9];
  soloInfo.tag = 12;
  if (params[9]) {
    solos.addParameters(&soloInfo, 1);
    solos.getParameterByTag(12)->setValue(fromBits(in[11]), false);
  }
  presonus::mixer::ChannelEnvironment env;
  env.globalParameters = in[37] ? &globals : nullptr;
  env.soloParameters = in[38] ? &solos : nullptr;
  env.panModeCache = in[39] ? params[10].get() : nullptr;
  env.soloBlockedA = in[35];
  env.soloBlockedB = in[36];
  env.panLaw = fromBits(in[31]);
  presonus::mixer::ChannelState state, pairState;
  state.mute = params[0].get();
  state.pan = params[1].get();
  state.linkedPan = params[2].get();
  state.level = params[3].get();
  state.solo = params[4].get();
  state.locateIndicator = params[5].get();
  state.locatePosition = params[6].get();
  state.mainAssign = params[7].get();
  state.monoAssign = params[8].get();
  state.soloModeCache = in[50] ? params[9].get() : nullptr;
  if (params[3])
    params[3]->normalized = fromBits(in[16]);
  if (params[6])
    params[6]->normalized = fromBits(in[17]);
  for (int i = 0; i < 3; ++i)
    state.coefficients[i] = fromBits(in[18 + i]);
  for (int i = 0; i < 2; ++i)
    state.soloCoefficients[i] = fromBits(in[21 + i]);
  state.gain = fromBits(in[23]);
  state.lastLocate = fromBits(in[24]);
  // Words 25..30 reserved for nontrivial surrounding state sentinels.
  state.linkSide = in[32];
  state.active = in[33];
  state.environment = &env;
  for (int i = 0; i < 8; ++i)
    state.updates[i] = in[40 + i];
  ParamInfo nameInfo = ParamInfo PARAM_STRING(90, "name", 0);
  StringParam name(nameInfo), pairName(nameInfo);
  name.setDefaultText("default");
  name.fromString(in[48] == 2 ? "custom" : "default", false);
  pairName.fromString("pair", false);
  if (in[48])
    state.name = &name;
  if (in[49] == 2)
    pairState.name = &pairName;
  Children children;
  const char *names[] = {"comp", "gate", "eq"};
  for (int i = 0; i < 3; ++i)
    if (in[51] & (1u << i))
      children.addChild(new Child(names[i], i));
  state.children = &children;
  Services services;
  services.linked = in[34];
  services.mutateActive = in[25];
  Channel c(state, services), pair(pairState, services);
  if (in[49])
    services.pair = &pair;
  c.mutateUpdate = in[26];
  trace.clear();
  int result = -1;
  switch (in[0]) {
  case 1:
    c.postDoUpdates();
    break;
  case 2:
    result = c.isLCRPanMode();
    break;
  case 3:
    c.removeLink();
    break;
  case 4:
    c.ChannelComponent::levelUpdate();
    break;
  case 5:
    c.linkChannelName();
    break;
  case 6:
    c.doUpdates();
    break;
  case 7:
    c.ChannelComponent::soloCoeffUpdate();
    break;
  case 8:
    c.checkFaderLocateSync();
    break;
  case 9:
    c.resetEQDyn();
    break;
  case 10:
    result = c.handleFaderLocate(fromBits(in[27]));
    break;
  default:
    return 2;
  }
  // Real CCL lookup getter traces are excluded as source-provider behavior;
  // explicit cache-hit parameters remain test observation boundaries.
  std::cout << result;
  for (float x : state.coefficients)
    std::cout << ' ' << bits(x);
  for (float x : state.soloCoefficients)
    std::cout << ' ' << bits(x);
  std::cout << ' ' << bits(state.gain);
  for (auto x : state.updates)
    std::cout << ' ' << x;
  std::cout << ' ' << (env.panModeCache != nullptr) << ' '
            << (state.soloModeCache != nullptr);
  std::cout << ' '
            << (params[1] ? bits(params[1]->NumericParam::getValue()) : 0)
            << ' '
            << (params[5] ? bits(params[5]->NumericParam::getValue()) : 0);
  std::cout << ' ' << (std::strcmp(pairName.getText(), "custom") == 0) << ' '
            << state.active;
  for (auto x : trace)
    std::cout << ' ' << x;
  std::cout << '\n';
}
