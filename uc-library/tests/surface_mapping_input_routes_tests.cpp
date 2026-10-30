#include "presonus/surface/mapping_input_routes.hpp"
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
using M = Presonus::Surface::MappingComponent;
namespace {
bool capture = false;
std::vector<std::string> events;
void emit(std::string s) {
  if (capture)
    events.push_back(s);
}
float floating(unsigned v) {
  float f;
  std::memcpy(&f, &v, 4);
  return f;
}
int integer(unsigned v) {
  int i;
  std::memcpy(&i, &v, 4);
  return i;
}
class Param : public Core::Portable::NumericParam {
public:
  using NumericParam::NumericParam;
  float getValue() const override {
    emit("get");
    return NumericParam::getValue();
  }
};
class Map final : public M {
public:
  Map() : M(presonus::surface::MappingRouteInit{}) {}
  void own(Core::Portable::Parameter *p) { paramList.add(p); }
  void paramChanged(Core::Portable::Parameter *, int) override {}
  void onIdle() override { std::abort(); }
  int getModifiers() const override { std::abort(); }
  int getRadioValue(int, int) const override { std::abort(); }
  int getBankScrollingOffset() const override { std::abort(); }
  Core::Portable::Parameter *getParamByTag(int) const override { std::abort(); }
  Core::Portable::Parameter *getMainScreenParamByTag(int) const override {
    std::abort();
  }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  bool areFadersLockedToMainMix() const override { std::abort(); }
  void onSelectedChannelChanged() override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
  void setRadioGroup(int, int, int, bool) override { std::abort(); }
  void onDeviceDisconnected() override { std::abort(); }
};
class Handler final : public Presonus::MixerAssignmentHandler {
public:
  int identity = 0;
  const char *getName() const override { std::abort(); }
  void updateConnections() override { std::abort(); }
  void onMappingParamChanged(Core::Portable::Parameter *) override {
    std::abort();
  }
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override {
    std::abort();
  }
  void onEncoderChanged(int v) override {
    emit("encoder:" + std::to_string(identity) + ":" +
         std::to_string(static_cast<unsigned>(v)));
  }
  void handleFootswitch(FootswitchMode m, bool v) override {
    emit("foot:" + std::to_string(identity) + ":" +
         std::to_string(static_cast<unsigned>(m)) + ":" + std::to_string(v));
  }
};
class SL final : public Presonus::Surface::SLMixerHandler {
public:
  const char *getName() const override { std::abort(); }
  void updateConnections() override { std::abort(); }
  void onModifiersChanged() override { std::abort(); }
  void onIdle() override { std::abort(); }
  void initialize(Core::Portable::Component *) override { std::abort(); }
  void setController(Presonus::IMappingController *) override { std::abort(); }
  void updatePanEncoderConnection() override { std::abort(); }
  void onMappingParamChanged(Core::Portable::Parameter *) override {
    std::abort();
  }
  bool handleMappingRadioGroup(Core::Portable::Parameter *) override {
    std::abort();
  }
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override {
    std::abort();
  }
  void paramChanged(Core::Portable::Parameter *, int) override { std::abort(); }
  void onSelectionChanged() override { std::abort(); }
  void onObjectChanged(ObjectChangeMessage) override { std::abort(); }
  void onComponentReplaced(const ReplaceArgs &) override { std::abort(); }
  void onEqEncoderModeChanged() override { std::abort(); }
  void onGeqScrollOffsetChanged() override { std::abort(); }
};
Core::Portable::ParamInfo info(float value) {
  Core::Portable::ParamInfo i{};
  i.type = Core::Portable::ParamInfo::kFloat;
  i.tag = 38;
  i.minValue = -8;
  i.maxValue = 128;
  i.defaultValue = value;
  return i;
}
} // namespace
extern "C" Core::Portable::Parameter *
realByTag(const Core::Portable::Component *,
          int) asm("__real__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Core::Portable::Parameter *wrapByTag(
    const Core::Portable::Component *c,
    int tag) asm("__wrap__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Core::Portable::Parameter *
wrapByTag(const Core::Portable::Component *c, int tag) {
  emit("bytag:" + std::to_string(tag));
  return realByTag(c, tag);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  std::string op;
  unsigned arg, normal, alternate, encoder, bits, count, checked = 0;
  while (in >> op >> arg >> normal >> alternate >> encoder >> bits >> count) {
    std::vector<std::string> wanted(count);
    for (auto &s : wanted)
      in >> s;
    auto definition = info(floating(bits));
    Map map;
    map.own(new Param(definition));
    Handler n, a, e;
    n.identity = 0;
    a.identity = 1;
    e.identity = 2;
    presonus::surface::MappingInputAccess::bind(map, normal ? &n : nullptr,
                                                alternate ? &a : nullptr,
                                                encoder ? &e : nullptr);
    events.clear();
    capture = true;
    if (op == "F")
      map.handleFootswitch(arg != 0);
    else if (op == "E")
      map.encoderChanged(integer(arg));
    else {
      const Presonus::IMappingController &interface = map;
      interface.encoderChanged(integer(arg));
    }
    capture = false;
    if (events != wanted) {
      std::cerr << "case " << checked << " got ";
      for (auto &s : events)
        std::cerr << s << ' ';
      std::cerr << " wanted ";
      for (auto &s : wanted)
        std::cerr << s << ' ';
      std::cerr << '\n';
      return 3;
    }
    ++checked;
  }
  // Compositional source evidence: routes reach actual recovered SLMixer
  // methods, actual Core-owned parameter38 and genuine CCL NumericParam
  // targets.
  {
    Map empty;
    bool rejected = false;
    try {
      empty.handleFootswitch(false);
    } catch (const std::logic_error &) {
      rejected = true;
    }
    if (!rejected)
      return 8;
  }
  unsigned composed = 0;
  for (int mode : {1, 3})
    for (bool pressed : {false, true}) {
      auto definition = info(static_cast<float>(mode));
      auto targetInfo = info(0);
      Core::Portable::NumericParam target(targetInfo);
      Map map;
      map.own(new Param(definition));
      SL handler;
      auto &vector =
          presonus::surface::SLMixerEncoderAccess::footswitchParameters(
              handler);
      if (!vector.resize(1))
        return 5;
      vector.add(&target);
      presonus::surface::SLMixerEncoderAccess::footswitchTarget(handler) =
          &target;
      presonus::surface::MappingInputAccess::bind(map, &handler, nullptr,
                                                  &handler);
      map.handleFootswitch(pressed);
      if (target.getValue() != (pressed ? 1.f : 0.f))
        return 6;
      map.encoderChanged(0);
      if (!presonus::surface::SLMixerEncoderAccess::timer(handler)
               .isExecuting())
        return 7;
      ++composed;
    }
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"real_SLMixer_compositions\":" << composed << "}\n";
}
