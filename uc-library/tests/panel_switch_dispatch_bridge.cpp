#include "presonus/panel/switch_control.hpp"
#include <array>
#include <cfenv>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using C = Presonus::Panel::Control;
using S = Presonus::Panel::SwitchControl;
using A = presonus::panel::ControlAccess;
using X = presonus::panel_binding::SwitchAccess;
using L = presonus::surface_panel_port::LEDStateAccess;
using P = Core::Portable::Parameter;
namespace {
bool tracing = false;
std::vector<std::string> events;
std::array<std::uint32_t, 17> input;
unsigned immediateCalls = 0;
template <class... T> void emit(const char *name, T... v) {
  if (!tracing)
    return;
  std::ostringstream s;
  s << name;
  ((s << ':' << v), ...);
  events.push_back(s.str());
}
float fromBits(std::uint32_t b) {
  float v;
  std::memcpy(&v, &b, 4);
  return v;
}
std::uint32_t bitsOf(float v) {
  std::uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}
void require(bool v) {
  if (!v)
    std::abort();
}
std::uint32_t allow(void *, S &) {
  emit("R", 0, input[7]);
  return input[7];
}
std::uint32_t immediate(void *, S &) {
  auto value = input[immediateCalls++ == 0 ? 8 : 9];
  emit("R", 1, value);
  return value;
}
float duration(void *, S &) {
  emit("R", 2, input[10]);
  return fromBits(input[10]);
}
void held(void *, S &) { emit("R", 3); }
void down(void *, S &) { emit("R", 4); }
void up(void *, S &) { emit("R", 5); }
void detach(void *, S &) {}
} // namespace
extern "C" std::uint32_t realParameter(P &, unsigned, std::uint32_t) asm(
    "__real__ZN8presonus13panel_"
    "binding23switchParameterDispatchERN4Core8Portable9ParameterEjj");
extern "C" std::uint32_t wrapParameter(P &, unsigned, std::uint32_t) asm(
    "__wrap__ZN8presonus13panel_"
    "binding23switchParameterDispatchERN4Core8Portable9ParameterEjj");
extern "C" std::uint32_t wrapParameter(P &p, unsigned op, std::uint32_t arg) {
  auto result = realParameter(p, op, arg);
  emit("P", op, arg, result);
  return result;
}
extern "C" void
realStart(C *, float,
          int) asm("__real__ZN8Presonus5Panel7Control10startTimerEfi");
extern "C" void
wrapStart(C *, float,
          int) asm("__wrap__ZN8Presonus5Panel7Control10startTimerEfi");
extern "C" void wrapStart(C *v, float value, int tag) {
  emit("A", bitsOf(value), std::uint32_t(tag));
  realStart(v, value, tag);
}
extern "C" void
realStop(C *, int) asm("__real__ZN8Presonus5Panel7Control9stopTimerEi");
extern "C" void
wrapStop(C *, int) asm("__wrap__ZN8Presonus5Panel7Control9stopTimerEi");
extern "C" void wrapStop(C *v, int tag) {
  emit("E", std::uint32_t(tag));
  realStop(v, tag);
}
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  return 1000000;
}
int main() {
  require(std::fegetround() == FE_TONEAREST);
  presonus::panel_binding::SwitchDispatchCallbacks callbacks{
      allow, immediate, duration, held, down, up};
  presonus::panel_binding::SwitchDetachBoundary receiver{nullptr, detach,
                                                         &callbacks};
  C other(88);
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line == "quit") {
      std::cout << "OK\n" << std::flush;
      return 0;
    }
    std::istringstream in(line);
    std::string op;
    in >> op;
    for (auto &v : input)
      in >> v;
    if (!in)
      return 2;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = -1.e30f;
    info.maxValue = fromBits(input[13]);
    info.defaultValue = fromBits(input[12]);
    Core::Portable::NumericParam p(info);
    p.enable(input[11] != 0);
    S value(7, 8, false);
    X::pressed(value) = std::uint8_t(input[3]);
    X::held(value) = std::uint8_t(input[4]);
    X::immediate(value) = std::uint8_t(input[2]);
    X::disabled(value) = std::uint8_t(input[1]);
    X::receiver(value) = input[6] ? &receiver : nullptr;
    L::setState(value, input[5] ? &p : nullptr,
                {0xffffffff, 17, 0, input[14], 0});
    auto &timers = A::timers();
    require(timers.count() == 0);
    require(timers.resize(8));
    auto seed = [&](C *owner, int tag) {
      auto *t = new C::Timer(owner, tag, 0.5f);
      require(timers.add(t));
    };
    if (input[15] & 1)
      seed(&other, 0x68656c64);
    if (input[15] & 2)
      seed(&value, 123);
    if (input[15] & 4)
      seed(&value, 0x68656c64);
    if (input[15] & 8)
      seed(&value, 0x68656c64);
    immediateCalls = 0;
    events.clear();
    tracing = true;
    if (op == "D")
      value.doSwitch();
    else if (op == "N")
      value.switchDown();
    else if (op == "U")
      value.switchUp();
    else if (op == "T")
      value.timerCallback(int(input[0]));
    else
      return 3;
    tracing = false;
    auto led = L::state(value);
    using LL = presonus::surface_panel_port::LEDLifecycleAccess;
    std::array<std::uint32_t, 19> state{
        led[0],
        unsigned(A::parameter(value) != nullptr),
        0,
        0,
        0,
        7,
        led[1],
        led[2],
        std::uint32_t(LL::savedBlink(value)),
        8,
        led[3],
        led[4],
        std::uint32_t(LL::on(value)),
        std::uint32_t(LL::off(value)),
        X::pressed(value),
        X::immediate(value),
        X::disabled(value),
        unsigned(X::receiver(value) != nullptr),
        X::held(value)};
    for (unsigned i = 0; i < state.size(); ++i) {
      if (i)
        std::cout << ' ';
      std::cout << state[i];
    }
    std::cout << " |";
    for (auto &e : events)
      std::cout << e << ';';
    std::cout << '|';
    for (int i = 0; i < timers.count(); ++i) {
      auto *t = timers.at(i);
      std::cout << (t->control == &value ? 1 : 2) << ':'
                << std::uint32_t(t->tag) << ',';
    }
    std::cout << '\n' << std::flush;
    X::receiver(value) = nullptr;
    A::parameter(value) = nullptr;
    while (timers.count()) {
      auto *t = timers.at(0);
      timers.remove(t);
      delete t;
    }
  }
}
