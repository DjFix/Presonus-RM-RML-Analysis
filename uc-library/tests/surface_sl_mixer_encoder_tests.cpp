#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
using E = Presonus::Surface::SLMixerHandler;
using X = presonus::surface::SLMixerEncoderAccess;
namespace {
bool capture = false, inside = false;
std::vector<std::string> events;
void emit(std::string s) {
  if (capture && !inside)
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
unsigned bits(float f) {
  unsigned v;
  std::memcpy(&v, &f, 4);
  return v;
}
class Parameter : public Core::Portable::NumericParam {
public:
  using NumericParam::NumericParam;
  float getValue() const override {
    emit("get");
    return NumericParam::getValue();
  }
  void setValue(float v, bool edit) override {
    emit("set:" + std::to_string(bits(v)) + ":" + std::to_string(edit));
    inside = true;
    NumericParam::setValue(v, edit);
    inside = false;
  }
};
class Mapping : public Presonus::IMappingController {
public:
  Core::Portable::Parameter *parameter = nullptr;
  int radio = 0;
  int getModifiers() const override { std::abort(); }
  int getRadioValue(int a, int b) const override {
    emit("radio:" + std::to_string(a) + ":" + std::to_string(b));
    return radio;
  }
  int getBankScrollingOffset() const override { std::abort(); }
  Core::Portable::Parameter *getParamByTag(int tag) const override {
    emit("param:" + std::to_string(static_cast<unsigned>(tag)));
    return parameter;
  }
  Core::Portable::Parameter *getMainScreenParamByTag(int tag) const override {
    emit("main:" + std::to_string(tag));
    return parameter;
  }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  bool areFadersLockedToMainMix() const override { std::abort(); }
  void encoderChanged(int) const override { std::abort(); }
  void onSelectedChannelChanged() override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
  void setRadioGroup(int, int, int, bool) override { std::abort(); }
  void onDeviceDisconnected() override { std::abort(); }
};
// Only test adapters implement unsupported original handlers, and fail on any
// unexpected call. The production partial class remains explicitly abstract.
class Fixture : public E {
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
  void handleFootswitch(FootswitchMode, bool) override { std::abort(); }
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
} // namespace
extern "C" bool realExecuting(const Presonus::DelayTimer *) asm(
    "__real__ZNK8Presonus10DelayTimer11isExecutingEv");
extern "C" bool wrapExecuting(const Presonus::DelayTimer *t) asm(
    "__wrap__ZNK8Presonus10DelayTimer11isExecutingEv");
extern "C" bool wrapExecuting(const Presonus::DelayTimer *t) {
  bool v = realExecuting(t);
  emit("E:" + std::to_string(v));
  return v;
}
extern "C" void
realBegin(Presonus::DelayTimer *,
          float) asm("__real__ZN8Presonus10DelayTimer11beginActionEf");
extern "C" void
wrapBegin(Presonus::DelayTimer *t,
          float value) asm("__wrap__ZN8Presonus10DelayTimer11beginActionEf");
extern "C" void wrapBegin(Presonus::DelayTimer *t, float value) {
  emit("A:" + std::to_string(bits(value)));
  realBegin(t, value);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string op;
  unsigned arg, controller, present, value, radio, executing, wantedResult,
      wantedExecuting, wantedSaved, count, checked = 0;
  while (input >> op >> arg >> controller >> present >> value >> radio >>
         executing >> wantedResult >> wantedExecuting >> wantedSaved >> count) {
    std::vector<std::string> wanted(count);
    for (auto &s : wanted)
      input >> s;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = -1;
    info.maxValue = 1;
    info.deltaValue = .01f;
    Parameter parameter(info);
    parameter.NumericParam::setValue(floating(value), false);
    Mapping mapping;
    mapping.parameter = present ? &parameter : nullptr;
    mapping.radio = integer(radio);
    Fixture handler;
    X::bind(handler, controller ? &mapping : nullptr);
    X::savedMeterMode(handler) = 77;
    auto &t = X::timer(handler);
    presonus::timing::DelayTimerAccess::set(
        t, {0, 1000, 0, .001f, executing != 0});
    events.clear();
    capture = true;
    unsigned result = 0xffffffff;
    if (op == "G")
      result = handler.getMappingParameter(integer(arg)) == &parameter;
    else if (op == "M")
      result = static_cast<unsigned>(handler.getMeterMode());
    else if (op == "A")
      result = handler.altKeyPressed();
    else if (op == "H") {
      const Presonus::Panel::IKeyInputDelegate &delegate = handler;
      result = delegate.altKeyPressed();
    } else
      handler.onEncoderChanged(integer(arg));
    capture = false;
    auto state = presonus::timing::DelayTimerAccess::get(t);
    if (events != wanted || result != wantedResult ||
        unsigned(state.executing) != wantedExecuting ||
        static_cast<unsigned>(X::savedMeterMode(handler)) != wantedSaved) {
      std::cerr << "case " << checked << ' ' << op << " result " << result
                << " expected " << wantedResult << " events ";
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
  std::cout << "{\"passed\":true,\"cases\":" << checked << "}\n";
}
