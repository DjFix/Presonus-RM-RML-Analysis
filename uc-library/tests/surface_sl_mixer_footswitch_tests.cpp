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
  int identity = 0;
  float getValue() const override {
    emit("get");
    return NumericParam::getValue();
  }
  void setValue(float v, bool edit) override {
    emit("set:" + std::to_string(identity) + ":" + std::to_string(bits(v)) +
         ":" + std::to_string(edit));
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
  std::ifstream in(argv[1]);
  unsigned mode, press, target, count, checked = 0;
  while (in >> mode >> press >> target >> count) {
    std::vector<unsigned> indices(count);
    for (auto &v : indices)
      in >> v;
    unsigned expectedCount;
    in >> expectedCount;
    std::vector<std::string> wanted(expectedCount);
    for (auto &s : wanted)
      in >> s;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    Parameter a(info), b(info), c(info), d(info);
    a.identity = 0;
    b.identity = 1;
    c.identity = 2;
    d.identity = 3;
    Parameter *parameters[] = {&a, &b, &c};
    Fixture handler;
    X::footswitchTarget(handler) = target ? &d : nullptr;
    auto &vector = X::footswitchParameters(handler);
    if (!vector.resize(3))
      return 4;
    for (auto index : indices)
      vector.add(parameters[index]);
    events.clear();
    capture = true;
    handler.handleFootswitch(
        static_cast<Presonus::MixerAssignmentHandler::FootswitchMode>(
            integer(mode)),
        press != 0);
    capture = false;
    if (events != wanted) {
      std::cerr << "case " << checked << " events ";
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
