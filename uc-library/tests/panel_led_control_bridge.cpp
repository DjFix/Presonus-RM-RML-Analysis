#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>
#include <new>
#include <sstream>
#include <string>
#include <vector>

// Provider requires NDEBUG; fixture requirements must remain active regardless.
#undef assert
#define assert(condition)                                                      \
  do {                                                                         \
    if (!(condition)) {                                                        \
      std::cerr << "requirement failed at " << __LINE__ << '\n';               \
      std::abort();                                                            \
    }                                                                          \
  } while (false)

using Core::Portable::IParamObserver;
using Core::Portable::Parameter;
using Presonus::Panel::Control;
using Presonus::Panel::LEDControl;
using A = presonus::panel::ControlAccess;
using S = presonus::surface_panel_port::LEDStateAccess;
using L = presonus::surface_panel_port::LEDLifecycleAccess;
namespace {
bool tracing = false;
bool watchArrays = false;
unsigned arrayEvents = 0;
LEDControl *tracked = nullptr;
Control::Timer *trackedTimer = nullptr;
std::vector<std::string> events;
template <typename... T> void emit(const std::string &kind, T... values) {
  if (!tracing)
    return;
  std::ostringstream s;
  s << kind;
  ((s << ':' << values), ...);
  events.push_back(s.str());
}
float floating(std::uint32_t bits) {
  float value;
  std::memcpy(&value, &bits, 4);
  return value;
}
std::uint32_t bits(float value) {
  std::uint32_t word;
  std::memcpy(&word, &value, 4);
  return word;
}
struct IO final : Presonus::Panel::IPanelIO {
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &message) override {
    emit("W", unsigned(message.bytes[0]), unsigned(message.bytes[1]),
         unsigned(message.bytes[2]), unsigned(message.bytes[3]));
    return -17;
  }
  int broadcast(Control *) override { std::abort(); }
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
};
std::array<std::uint32_t, 14> state(LEDControl &v) {
  auto s = S::state(v);
  return {s[0],
          unsigned(A::parameter(v) != nullptr),
          unsigned(A::altParameter(v) != nullptr),
          unsigned(A::tertiaryParameter(v) != nullptr),
          unsigned(A::io(v) != nullptr),
          std::uint32_t(A::tag(v)),
          s[1],
          s[2],
          std::uint32_t(L::savedBlink(v)),
          std::uint32_t(L::group(v)),
          s[3],
          s[4],
          std::uint32_t(L::on(v)),
          std::uint32_t(L::off(v))};
}
} // namespace

extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void *__real__Znam(std::size_t);
extern "C" void __real__ZdaPv(void *);
extern "C" void __real__ZdaPvm(void *, std::size_t);
extern "C" void *__wrap__Znam(std::size_t size) {
  if (watchArrays)
    ++arrayEvents;
  return __real__Znam(size);
}
extern "C" void __wrap__ZdaPv(void *p) {
  if (watchArrays && p)
    ++arrayEvents;
  __real__ZdaPv(p);
}
extern "C" void __wrap__ZdaPvm(void *p, std::size_t size) {
  if (watchArrays && p)
    ++arrayEvents;
  __real__ZdaPvm(p, size);
}
extern "C" void __wrap__ZdlPv(void *p) {
  if (tracing && p && p == trackedTimer) {
    trackedTimer = nullptr;
    emit("Y");
  }
  if (tracing && p && p == tracked) {
    tracked = nullptr;
    emit("X");
  }
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (tracing && p && p == trackedTimer) {
    trackedTimer = nullptr;
    emit("Y");
  }
  if (tracing && p && p == tracked) {
    assert(size == sizeof(LEDControl));
    tracked = nullptr;
    emit("X");
  }
  __real__ZdlPvm(p, size);
}
extern "C" void __real__ZN8Presonus5Panel7ControlD2Ev(Control *);
extern "C" void __wrap__ZN8Presonus5Panel7ControlD2Ev(Control *v) {
  if (v == tracked)
    emit("D");
  __real__ZN8Presonus5Panel7ControlD2Ev(v);
}
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  emit("R");
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
}
extern "C" void __real__ZN4Core8Portable9Parameter7changedEv(Parameter *);
extern "C" void __wrap__ZN4Core8Portable9Parameter7changedEv(Parameter *p) {
  emit("C");
  __real__ZN4Core8Portable9Parameter7changedEv(p);
}
extern "C" float __real__ZNK4Core8Portable12NumericParam8getValueEv(
    const Core::Portable::NumericParam *);
extern "C" float __wrap__ZNK4Core8Portable12NumericParam8getValueEv(
    const Core::Portable::NumericParam *p) {
  const auto value = __real__ZNK4Core8Portable12NumericParam8getValueEv(p);
  emit("G", bits(value));
  return value;
}
extern "C" void __real__ZN8Presonus5Panel7Control9stopTimerEi(Control *, int);
extern "C" void __wrap__ZN8Presonus5Panel7Control9stopTimerEi(Control *p,
                                                              int tag) {
  emit("E", std::uint32_t(tag));
  __real__ZN8Presonus5Panel7Control9stopTimerEi(p, tag);
}
extern "C" void __real__ZN8Presonus5Panel7Control10startTimerEfi(Control *,
                                                                 float, int);
extern "C" void __wrap__ZN8Presonus5Panel7Control10startTimerEfi(Control *p,
                                                                 float seconds,
                                                                 int tag) {
  emit("A", bits(seconds), std::uint32_t(tag));
  __real__ZN8Presonus5Panel7Control10startTimerEfi(p, seconds, tag);
}
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  return 1000000;
}
extern "C" void ctor1(LEDControl *, int, int,
                      int) asm("_ZN8Presonus5Panel10LEDControlC1Eiii");
extern "C" void ctor2(LEDControl *, int, int,
                      int) asm("_ZN8Presonus5Panel10LEDControlC2Eiii");
extern "C" void dtor1(LEDControl *) asm("_ZN8Presonus5Panel10LEDControlD1Ev");
extern "C" void dtor0(LEDControl *) asm("_ZN8Presonus5Panel10LEDControlD0Ev");
extern "C" void ledLifecycleEntry(Control *, unsigned);

int main(int argc, char **argv) {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 100;
  Core::Portable::NumericParam parameter(info);
  IO endpoint;
  Control other1(1), other2(2);
  if (argc == 2 && std::string(argv[1]) == "--smoke") {
    Core::Portable::NumericParam second(info), third(info);
    for (unsigned slot : {2U, 3U}) {
      auto *value = new LEDControl(7, 8, -1);
      value->setParameter(&parameter, 0);
      value->setAltParameter(&second);
      value->setTertiaryParameter(&third);
      value->startTimer(0.5f, 123);
      assert(A::timers().count() == 1);
      trackedTimer = A::timers().at(0);
      tracked = value;
      events.clear();
      tracing = true;
      auto **table = *reinterpret_cast<void ***>(value);
      assert(table[2] == reinterpret_cast<void *>(&dtor1));
      assert(table[3] == reinterpret_cast<void *>(&dtor0));
      ledLifecycleEntry(value, slot);
      assert(trackedTimer == nullptr && A::timers().count() == 0);
      assert((tracked == nullptr) == (slot == 3));
      const std::vector<std::string> expected =
          slot == 3 ? std::vector<std::string>{"D", "Y", "R", "R", "R", "X"}
                    : std::vector<std::string>{"D", "Y", "R", "R", "R"};
      assert(events == expected);
      events.clear();
      parameter.changed();
      second.changed();
      third.changed();
      assert(events == std::vector<std::string>({"C", "C", "C"}));
      tracing = false;
      if (slot == 2)
        ::operator delete(value);
      tracked = nullptr;
    }
    std::cout << "PASS actual D1/D0 targets, timer/object deallocation and "
                 "three observer cleanups\n";
    return 0;
  }
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line == "quit") {
      std::cout << "OK\n" << std::flush;
      break;
    }
    std::istringstream in(line);
    std::string op;
    std::array<std::uint32_t, 17> x{};
    in >> op;
    for (auto &v : x)
      in >> v;
    if (!in)
      return 2;
    // arg,message,present,parambits,io,disabled,queue,cache,tag,color,
    // dirty,savedBlink,group,match,blink,on,off.
    auto &dispatch = presonus::surface_panel_port::ledDispatchState();
    dispatch.dirty.removeAll();
    assert(dispatch.dirty.resize(8));
    assert(dispatch.dirty.getCapacity() >= 8);
    parameter.setValueFast(1.f);
    parameter.setValueFast(floating(x[3]));
    auto *v = static_cast<LEDControl *>(::operator new(sizeof(LEDControl)));
    if (op == "C2")
      ctor2(v, int(x[8]), int(x[12]), int(x[13]));
    else
      ctor1(v, int(x[8]), int(x[12]), int(x[13]));
    assert(dynamic_cast<LEDControl *>(static_cast<Control *>(v)) == v);
    auto **table = *reinterpret_cast<void ***>(v);
    assert(table[2] == reinterpret_cast<void *>(&dtor1));
    assert(table[3] == reinterpret_cast<void *>(&dtor0));
    if (op != "C1" && op != "C2") {
      S::setState(*v, x[2] ? &parameter : nullptr,
                  {x[7], x[9], x[10], x[13], x[14]});
      A::io(*v) = x[4] ? &endpoint : nullptr;
      L::savedBlink(*v) = int(x[11]);
      L::on(*v) = int(x[15]);
      L::off(*v) = int(x[16]);
    }
    if (x[6])
      dispatch.dirty.add(&other1);
    if (x[6] == 1)
      dispatch.dirty.add(v);
    if (x[6] == 2)
      dispatch.dirty.add(&other2);
    dispatch.disabled = std::uint8_t(x[5]);
    events.clear();
    tracked = v;
    tracing = true;
    arrayEvents = 0;
    // Actual forwarded timer helpers have their separately proved allocation
    // domain. All direct queue/parameter/transmission/lifecycle paths are
    // checked for absence of array allocations under sufficient capacity.
    watchArrays = op != "S" && op != "E" && op != "B";
    auto result = state(*v);
    bool ended = false, deleted = false;
    if (op == "D1" || op == "D0") {
      ledLifecycleEntry(v, op == "D0" ? 3 : 2);
      ended = true;
      deleted = op == "D0";
      assert((tracked == nullptr) == deleted);
    } else {
      if (op == "K")
        emit("K", v->castTo(int(x[0])) == v ? 1 : 0);
      else if (op == "I")
        v->setInverseMode(x[0] != 0);
      else if (op == "P")
        v->paramChanged(x[2] ? &parameter : nullptr, int(x[1]));
      else if (op == "S")
        v->startBlinking(floating(x[0]));
      else if (op == "E")
        v->stopBlinking();
      else if (op == "B")
        v->timerCallback(int(x[0]));
      else if (op == "T")
        v->transmit();
      else if (op != "C1" && op != "C2")
        return 3;
      result = state(*v);
    }
    tracing = false;
    watchArrays = false;
    assert(arrayEvents == 0);
    for (auto value : result)
      std::cout << value << ' ';
    std::cout << '|';
    for (const auto &event : events)
      std::cout << event << ';';
    std::cout << '|';
    for (int i = 0; i < dispatch.dirty.count(); ++i) {
      const auto *p = dispatch.dirty.at(i);
      std::cout << (p == v ? 1 : p == &other1 ? 2 : 3) << ',';
    }
    std::cout << '\n' << std::flush;
    dispatch.dirty.removeAll();
    if (!ended) {
      delete v;
    } else if (!deleted)
      ::operator delete(v);
    tracked = nullptr;
    assert(A::timers().count() == 0);
  }
}
