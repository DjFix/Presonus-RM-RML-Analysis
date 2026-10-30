#include "presonus/panel/switch_control.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <sstream>
#include <string>
#include <vector>

#define REQUIRE(condition)                                                     \
  do {                                                                         \
    if (!(condition)) {                                                        \
      std::cerr << "requirement at " << __LINE__ << '\n';                      \
      std::abort();                                                            \
    }                                                                          \
  } while (false)
using Core::Portable::IParamObserver;
using Core::Portable::Parameter;
using Presonus::Panel::Control;
using Presonus::Panel::SwitchControl;
using A = presonus::panel::ControlAccess;
using S = presonus::panel_binding::SwitchAccess;
using LS = presonus::surface_panel_port::LEDStateAccess;
using LL = presonus::surface_panel_port::LEDLifecycleAccess;
namespace {
bool tracing = false;
SwitchControl *tracked = nullptr;
Control::Timer *timer = nullptr;
unsigned resets = 0;
void *receiverContext = nullptr;
std::vector<std::string> events;
template <class... T> void emit(const std::string &kind, T... v) {
  if (!tracing)
    return;
  std::ostringstream out;
  out << kind;
  ((out << ':' << v), ...);
  events.push_back(out.str());
}
void detach(void *context, SwitchControl &value) {
  REQUIRE(context == receiverContext);
  REQUIRE(dynamic_cast<SwitchControl *>(static_cast<Control *>(&value)) ==
          &value);
  emit("H", unsigned(S::pressed(value)), unsigned(S::immediate(value)),
       unsigned(S::disabled(value)), unsigned(S::held(value)),
       unsigned(A::parameter(value) != nullptr));
}
std::array<std::uint32_t, 19> state(SwitchControl &v) {
  auto s = LS::state(v);
  return {s[0],
          unsigned(A::parameter(v) != nullptr),
          unsigned(A::altParameter(v) != nullptr),
          unsigned(A::tertiaryParameter(v) != nullptr),
          unsigned(A::io(v) != nullptr),
          std::uint32_t(A::tag(v)),
          s[1],
          s[2],
          std::uint32_t(LL::savedBlink(v)),
          std::uint32_t(LL::group(v)),
          s[3],
          s[4],
          std::uint32_t(LL::on(v)),
          std::uint32_t(LL::off(v)),
          S::pressed(v),
          S::immediate(v),
          S::disabled(v),
          unsigned(S::receiver(v) != nullptr),
          S::held(v)};
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (tracing && p && p == timer) {
    timer = nullptr;
    emit("Y");
  }
  if (tracing && p && p == tracked) {
    tracked = nullptr;
    emit("X");
  }
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (tracing && p && p == timer) {
    timer = nullptr;
    emit("Y");
  }
  if (tracing && p && p == tracked) {
    REQUIRE(size == sizeof(SwitchControl));
    tracked = nullptr;
    emit("X");
  }
  __real__ZdlPvm(p, size);
}
extern "C" void __real__ZN8Presonus5Panel7ControlD2Ev(Control *);
extern "C" void __wrap__ZN8Presonus5Panel7ControlD2Ev(Control *p) {
  if (p == tracked)
    emit("D");
  __real__ZN8Presonus5Panel7ControlD2Ev(p);
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
extern "C" void
__real__ZN8presonus13panel_binding20resetSwitchParameterERN4Core8Portable9ParameterE(
    Parameter &);
extern "C" void
__wrap__ZN8presonus13panel_binding20resetSwitchParameterERN4Core8Portable9ParameterE(
    Parameter &p) {
  ++resets;
  emit("V", 0);
  __real__ZN8presonus13panel_binding20resetSwitchParameterERN4Core8Portable9ParameterE(
      p);
}
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  return 1000000;
}
extern "C" void ctor1(SwitchControl *, int, int,
                      bool) asm("_ZN8Presonus5Panel13SwitchControlC1Eiib");
extern "C" void ctor2(SwitchControl *, int, int,
                      bool) asm("_ZN8Presonus5Panel13SwitchControlC2Eiib");
extern "C" void
dtor1(SwitchControl *) asm("_ZN8Presonus5Panel13SwitchControlD1Ev");
extern "C" void
dtor2(SwitchControl *) asm("_ZN8Presonus5Panel13SwitchControlD2Ev");
extern "C" void
dtor0(SwitchControl *) asm("_ZN8Presonus5Panel13SwitchControlD0Ev");
extern "C" void switchLifecycleEntry(Control *, unsigned);

int main(int argc, char **argv) {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 100;
  info.defaultValue = 7.5f;
  Core::Portable::NumericParam parameter(info), second(info), third(info);
  Control other1(1), other2(2);
  receiverContext = &parameter;
  presonus::panel_binding::SwitchDetachBoundary receiver{receiverContext,
                                                         detach};
  auto &dispatch = presonus::surface_panel_port::ledDispatchState();
  if (argc == 2 && std::string(argv[1]) == "--smoke") {
    for (unsigned mode : {2U, 3U, 4U}) {
      auto *v = new SwitchControl(7, 8, true);
      S::receiver(*v) = &receiver;
      v->setParameter(&parameter, 0);
      v->setAltParameter(&second);
      v->setTertiaryParameter(&third);
      parameter.setValueFast(42.25f);
      resets = 0;
      v->disableControl(true, true);
      REQUIRE(resets == 1 && parameter.getValue() == 7.5f &&
              S::disabled(*v) == 1);
      v->startTimer(0.5f, 123);
      REQUIRE(A::timers().count() == 1);
      timer = A::timers().at(0);
      dispatch.dirty.removeAll();
      REQUIRE(dispatch.dirty.add(&other1));
      tracked = v;
      events.clear();
      tracing = true;
      auto **table = *reinterpret_cast<void ***>(v);
      REQUIRE(table[2] == reinterpret_cast<void *>(&dtor1));
      REQUIRE(table[3] == reinterpret_cast<void *>(&dtor0));
      if (mode == 4)
        dtor2(v);
      else
        switchLifecycleEntry(v, mode);
      REQUIRE(timer == nullptr && A::timers().count() == 0);
      REQUIRE((tracked == nullptr) == (mode == 3));
      std::vector<std::string> expected{"H:0:1:1:0:1", "D", "Y", "R", "R", "R"};
      if (mode == 3)
        expected.push_back("X");
      REQUIRE(events == expected);
      REQUIRE(dispatch.dirty.count() == 1 && dispatch.dirty.at(0) == &other1);
      parameter.changed();
      second.changed();
      third.changed();
      REQUIRE(events == expected);
      tracing = false;
      dispatch.dirty.removeAll();
      if (mode != 3)
        ::operator delete(v);
      tracked = nullptr;
    }
    std::cout
        << "PASS Switch D1/D2/D0 actual targets, detach boundary, object/timer "
           "delete, observers, dirty list, actual CCL reset(false)\n";
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
    std::array<std::uint32_t, 20> x{};
    in >> op;
    for (auto &v : x)
      in >> v;
    if (!in)
      return 2;
    parameter.setValueFast(42.25f);
    dispatch.dirty.removeAll();
    REQUIRE(dispatch.dirty.resize(8));
    auto *v =
        static_cast<SwitchControl *>(::operator new(sizeof(SwitchControl)));
    if (op == "C2")
      ctor2(v, int(x[8]), int(x[9]), x[0] != 0);
    else
      ctor1(v, int(x[8]), int(x[9]), x[0] != 0);
    auto **table = *reinterpret_cast<void ***>(v);
    REQUIRE(table[2] == reinterpret_cast<void *>(&dtor1));
    REQUIRE(table[3] == reinterpret_cast<void *>(&dtor0));
    REQUIRE(dynamic_cast<SwitchControl *>(static_cast<Control *>(v)) == v);
    if (op != "C1" && op != "C2") {
      LS::setState(*v, x[2] ? &parameter : nullptr,
                   {x[10], x[11], x[12], x[14], x[15]});
      LL::savedBlink(*v) = int(x[13]);
      LL::on(*v) = int(x[16]);
      LL::off(*v) = int(x[17]);
      S::pressed(*v) = std::uint8_t(x[6]);
      S::immediate(*v) = std::uint8_t(x[4]);
      S::disabled(*v) = std::uint8_t(x[5]);
      S::held(*v) = std::uint8_t(x[7]);
      S::receiver(*v) = x[3] ? &receiver : nullptr;
    }
    if (x[18] > 0)
      REQUIRE(dispatch.dirty.add(&other1));
    if (x[18] > 1)
      REQUIRE(dispatch.dirty.add(&other2));
    dispatch.disabled = std::uint8_t(x[19]);
    resets = 0;
    events.clear();
    tracked = v;
    tracing = true;
    auto after = state(*v);
    bool ended = false, deleted = false;
    if (op == "D1" || op == "D2" || op == "D0") {
      if (op == "D2")
        dtor2(v);
      else
        switchLifecycleEntry(v, op == "D0" ? 3 : 2);
      ended = true;
      deleted = op == "D0";
      REQUIRE((tracked == nullptr) == deleted);
    } else {
      if (op == "K")
        emit("K", v->castTo(int(x[0])) == v ? 1 : 0);
      else if (op == "G")
        emit("G", unsigned(v->isImmediate()));
      else if (op == "S")
        v->setImmediate(x[0] != 0);
      else if (op == "I")
        v->disableControl(x[0] != 0, x[1] != 0);
      else if (op != "C1" && op != "C2")
        return 3;
      after = state(*v);
    }
    REQUIRE(resets == unsigned(op == "I" && x[0] && x[1] && x[2]));
    REQUIRE(parameter.getValue() == (resets ? 7.5f : 42.25f));
    REQUIRE(dispatch.dirty.count() == int(x[18]) && dispatch.disabled == x[19]);
    tracing = false;
    for (auto value : after)
      std::cout << value << ' ';
    std::cout << '|';
    for (auto &e : events)
      std::cout << e << ';';
    std::cout << '|';
    for (int i = 0; i < dispatch.dirty.count(); ++i) {
      REQUIRE(dispatch.dirty.at(i) == (i == 0 ? &other1 : &other2));
      if (i)
        std::cout << ',';
      std::cout << i + 2;
    }
    std::cout << '\n' << std::flush;
    dispatch.dirty.removeAll();
    if (!ended)
      delete v;
    else if (!deleted)
      ::operator delete(v);
    tracked = nullptr;
    REQUIRE(A::timers().count() == 0);
  }
}
