#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
namespace surface_test {
extern void (*observerTap)(bool, Core::Portable::Parameter *,
                           Core::Portable::IParamObserver *);
}
Core::Portable::Parameter *knownParameters[2]{};
Core::Portable::IParamObserver *expectedObserver = nullptr;
int notifications[2]{};
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
  void paramChanged(Core::Portable::Parameter *p, int message) override {
    if (message == Core::Portable::Parameter::kChanged) {
      for (int i = 0; i < 2; ++i)
        if (p == knownParameters[i])
          ++notifications[i];
    }
  }
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
void tap(bool add, Core::Portable::Parameter *p,
         Core::Portable::IParamObserver *o) {
  if (o != expectedObserver)
    std::abort();
  for (int i = 0; i < 2; ++i)
    if (knownParameters[i] == p) {
      emit(std::string(add ? "add:" : "remove:") + std::to_string(i) + ":1");
      return;
    }
  std::abort();
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  unsigned oldfirst, oldsecond, first, second, count, checked = 0,
                                                      delivered = 0;
  while (in >> oldfirst >> oldsecond >> first >> second >> count) {
    std::vector<std::string> wanted(count);
    for (auto &s : wanted)
      in >> s;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = 0;
    info.maxValue = 1;
    Parameter a(info), b(info);
    knownParameters[0] = &a;
    knownParameters[1] = &b;
    auto pointer = [&](unsigned v) -> Core::Portable::Parameter * {
      return v ? knownParameters[v - 1] : nullptr;
    };
    Fixture handler;
    expectedObserver = static_cast<Core::Portable::IParamObserver *>(&handler);
    surface_test::observerTap = tap;
    handler.setDigitalParams(pointer(oldfirst), pointer(oldsecond));
    events.clear();
    capture = true;
    handler.setDigitalParams(pointer(first), pointer(second));
    capture = false;
    if (events != wanted || X::digitalFirst(handler) != pointer(first) ||
        X::digitalSecond(handler) != pointer(second)) {
      std::cerr << "case " << checked << " mismatch\n";
      return 3;
    }
    int expected[2] = {int(first == 1) + int(second == 1),
                       int(first == 2) + int(second == 2)};
    notifications[0] = notifications[1] = 0;
    a.changed();
    b.changed();
    if (notifications[0] != expected[0] || notifications[1] != expected[1]) {
      std::cerr << "notification composition " << checked << ' '
                << notifications[0] << ' ' << notifications[1] << " expected "
                << expected[0] << ' ' << expected[1] << '\n';
      return 4;
    }
    delivered += notifications[0] + notifications[1];
    handler.setDigitalParams(nullptr, nullptr);
    notifications[0] = notifications[1] = 0;
    a.changed();
    b.changed();
    if (notifications[0] || notifications[1])
      return 5;
    surface_test::observerTap = nullptr;
    expectedObserver = nullptr;
    knownParameters[0] = knownParameters[1] = nullptr;
    ++checked;
  }
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"actual_CCL_notifications\":" << delivered << "}\n";
}
