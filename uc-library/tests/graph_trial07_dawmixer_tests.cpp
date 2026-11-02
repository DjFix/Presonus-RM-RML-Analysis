#include "presonus/surface/DAWMixerHandler.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>
using Core::Portable::Component;
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using Core::Portable::ParamList;
namespace {
using Input = std::array<long long, 24>;
std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, sizeof result);
  return result;
}
float number(std::uint32_t value) {
  float result;
  std::memcpy(&result, &value, sizeof result);
  return result;
}
struct RecordingParam : NumericParam {
  int identity;
  std::vector<std::string> &events;
  RecordingParam(int identity, int tag, float initial,
                 std::vector<std::string> &events)
      : NumericParam(*newInfo(tag), true), identity(identity), events(events) {
    NumericParam::setValue(initial, false);
  }
  static ParamInfo *newInfo(int tag) {
    ParamInfo info =
        PARAM_FLOAT(tag, "test", -100, 100, 0, .01, nullptr, nullptr, 0, 0);
    return new ParamInfo(info);
  }
  void setValue(float value, bool edit) override {
    events.push_back("set:" + std::to_string(identity) + ":" +
                     std::to_string(bits(value)) + ":" + std::to_string(edit));
    NumericParam::setValue(value, edit);
  }
};
struct TestComponent : Component {
  void add(Parameter *parameter) { paramList.add(parameter); }
};
struct Dependencies : presonus::surface::DAWMixerDependencies {
  const Input &x;
  std::vector<std::string> events;
  TestComponent channelComponent, slotComponent;
  ParamList automation;
  std::unique_ptr<RecordingParam> mappingParam;
  std::unordered_map<Parameter *, int> ids;
  std::array<RecordingParam *, 4> autoParams{};
  std::unique_ptr<RecordingParam> argument;
  static Presonus::DAWChannel *channel() {
    return reinterpret_cast<Presonus::DAWChannel *>(0x330000);
  }
  explicit Dependencies(const Input &x) : x(x) {
    for (int tag : {1, 2, 3, 6, 8, 9, 11, 12, 14, 15, 18, 1000}) {
      if (!x[17])
        continue;
      auto *p = new RecordingParam(10000 + tag, tag,
                                   tag == 18 ? number(x[19]) : .25f, events);
      ids[p] = 10000 + tag;
      channelComponent.add(p);
    }
    for (int tag : {1, 2, 3}) {
      if (!x[17])
        continue;
      auto *p = new RecordingParam(20000 + tag, tag, .25f, events);
      ids[p] = 20000 + tag;
      slotComponent.add(p);
    }
    for (int tag = 0; tag != 4; ++tag) {
      if (!(x[18] & (1 << tag)))
        continue;
      auto *p = new RecordingParam(30000 + tag, tag, .25f, events);
      ids[p] = 30000 + tag;
      autoParams[tag] = p;
      automation.add(p);
    }
    mappingParam = std::make_unique<RecordingParam>(40018, 18, .25f, events);
    ids[mappingParam.get()] = 40018;
    argument = std::make_unique<RecordingParam>(60000, static_cast<int>(x[11]),
                                                .25f, events);
    if (auto *p = channelComponent.getParameterByTag(9))
      p->enable(x[20] != 0);
    if (auto *p = slotComponent.getParameterByTag(2))
      p->enable(x[20] != 0);
    events.clear();
  }
  int identity(Parameter *p) const {
    if (!p)
      return 0;
    auto it = ids.find(p);
    if (it != ids.end())
      return it->second;
    return static_cast<int>(reinterpret_cast<std::uintptr_t>(p));
  }
  Presonus::DAWChannel *focusChannel() override {
    events.push_back("focus");
    return x[21] ? channel()
                 : reinterpret_cast<Presonus::DAWChannel *>(0x331000);
  }
  Presonus::DAWChannel *mainChannel() override {
    events.push_back("main");
    return x[5] ? channel() : nullptr;
  }
  int selectedMix() const override {
    const_cast<Dependencies *>(this)->events.push_back("selected");
    return static_cast<int>(x[1]);
  }
  bool showStripMeters() const override { return x[16] != 0; }
  Component *component(Presonus::DAWChannel *) const override {
    return const_cast<TestComponent *>(&channelComponent);
  }
  Presonus::DAWDeviceFolder *folder(Presonus::DAWChannel *,
                                    bool cue) const override {
    return x[6] ? reinterpret_cast<Presonus::DAWDeviceFolder *>(cue ? 0x350000
                                                                    : 0x340000)
                : nullptr;
  }
  int usedCount(Presonus::DAWDeviceFolder *) const override {
    return static_cast<int>(x[7]);
  }
  Component *slot(Presonus::DAWDeviceFolder *, int index) const override {
    return index < x[8] && x[9] ? const_cast<TestComponent *>(&slotComponent)
                                : nullptr;
  }
  const char *channelType(Presonus::DAWChannel *) const override {
    return x[10] == 0 ? nullptr : x[10] == 1 ? "AudioOutput" : "other";
  }
  void connect(const char *name, Parameter *p, const char *formatter,
               bool flag) override {
    events.push_back(
        std::string("connect:") + name + ":" + std::to_string(identity(p)) +
        ":" + (formatter ? formatter : "-") + ":" + std::to_string(flag));
  }
  unsigned modifiers() {
    events.push_back("modifiers");
    return x[13];
  }
  Parameter *mappingParameter(int tag) {
    events.push_back("mappingParam:" + std::to_string(tag));
    return x[22] ? mappingParam.get() : nullptr;
  }
  void mappingFocusChanged() { events.push_back("mappingFocus"); }
  void assignChannels() override { events.push_back("assign"); }
  void assignControlLinkTargets() override { events.push_back("control"); }
  void assignSelectedChannelTargets() override {
    events.push_back("updateFocus");
  }
  void assignFlexStrip() override { events.push_back("names"); }
};
struct Controller : Presonus::IMappingController {
  Dependencies &dependencies;
  explicit Controller(Dependencies &d) : dependencies(d) {}
  int getModifiers() const override { return dependencies.modifiers(); }
  int getRadioValue(int, int) const override { return 0; }
  int getBankScrollingOffset() const override { return 0; }
  Parameter *getParamByTag(int) const override { return nullptr; }
  Parameter *getMainScreenParamByTag(int tag) const override {
    return dependencies.mappingParameter(tag);
  }
  bool isDisplayEncoderLocked() const override { return false; }
  bool areFadersLockedToMainMix() const override { return false; }
  void encoderChanged(int) const override {}
  void onSelectedChannelChanged() override {
    dependencies.mappingFocusChanged();
  }
  void selectedChannelUpdated() override {}
  void setRadioGroup(int, int, int, bool) override {}
  void onDeviceDisconnected() override {}
};
void run(const Input &x) {
  Dependencies deps(x);
  Controller controller(deps);
  presonus::surface::DAWMixerState state;
  state.clientPresent = x[2];
  state.mappingController = x[3] ? &controller : nullptr;
  state.channelNamesVisible = x[12];
  state.shift = x[14];
  state.stripMeters = x[15];
  state.mainGroup = reinterpret_cast<Presonus::DAWChannelGroup *>(0x380100);
  state.inputGroup = reinterpret_cast<Presonus::DAWChannelGroup *>(0x380200);
  state.outputGroup = reinterpret_cast<Presonus::DAWChannelGroup *>(0x380300);
  Presonus::Surface::DAWMixerHandler handler(deps, state, deps.automation);
  Presonus::Surface::DAWMixerHandler::MixTargets targets;
  if (x[23]) {
    targets.level = reinterpret_cast<Parameter *>(50000);
    targets.mute = reinterpret_cast<Parameter *>(50001);
    targets.pan = reinterpret_cast<Parameter *>(50002);
    targets.extraPan = reinterpret_cast<Parameter *>(50003);
  }
  switch (x[0]) {
  case 1:
    handler.updatePanEncoderConnection();
    break;
  case 2:
    handler.onChannelsChanged(
        reinterpret_cast<Presonus::DAWChannelGroup *>(0x380000 + x[4] * 0x100));
    break;
  case 3:
    handler.getMixTargets(targets, x[5] ? deps.channel() : nullptr, x[1]);
    break;
  case 4:
    handler.assignMainChannel();
    break;
  case 5:
    handler.onChannelParamChanged(x[5] ? deps.channel() : nullptr,
                                  deps.argument.get());
    break;
  case 6:
    handler.onModifiersChanged();
    break;
  case 7:
    handler.onMappingParamChanged(deps.argument.get());
    break;
  case 8:
    handler.onFocusChannelChanged();
    break;
  case 9:
    handler.onSlotCountChanged(nullptr);
    break;
  case 10:
    handler.syncAutomationParams(x[5] ? deps.channel() : nullptr);
    break;
  default:
    throw std::runtime_error("invalid method");
  }
  std::cout << int(state.shift) << ',' << int(state.stripMeters);
  for (auto *p : {targets.level, targets.mute, targets.pan, targets.extraPan})
    std::cout << ',' << (x[0] == 3 ? deps.identity(p) : 0);
  for (auto *p : deps.autoParams)
    std::cout << ',' << (p ? bits(p->getValue()) : bits(.25f));
  std::cout << ',' << bits(deps.mappingParam->getValue());
  for (const auto &e : deps.events)
    std::cout << ';' << e;
  std::cout << '\n';
}
} // namespace
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    Input x{};
    for (auto &v : x)
      if (!(input >> v))
        return 2;
    run(x);
  }
}
