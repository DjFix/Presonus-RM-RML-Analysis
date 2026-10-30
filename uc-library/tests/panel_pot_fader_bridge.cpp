#include "presonus/panel/param_edit_handler.hpp"
#include "presonus/panel/pot_fader_control.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <sstream>
#include <string>
#include <vector>
using C = Presonus::Panel::Control;
using Pot = Presonus::Panel::PotControl;
using Fader = Presonus::Panel::FaderControl;
using P = Core::Portable::Parameter;
using Observer = Core::Portable::IParamObserver;
using A = presonus::panel::ControlAccess;
using Edits = presonus::panel::ParamEditHandlerAccess;
using Handler = Presonus::Panel::ParamEditHandler;
#define ABI(name, spelling, result, ...)                                       \
  extern "C" result name(__VA_ARGS__) asm(spelling)
ABI(pc1, "_ZN8Presonus5Panel10PotControlC1Ei", void, C *, int);
ABI(pc2, "_ZN8Presonus5Panel10PotControlC2Ei", void, C *, int);
ABI(pd1, "_ZN8Presonus5Panel10PotControlD1Ev", void, C *);
ABI(pd0, "_ZN8Presonus5Panel10PotControlD0Ev", void, C *);
ABI(pk, "_ZN8Presonus5Panel10PotControl6castToEi", void *, C *, int);
ABI(pb, "_ZN8Presonus5Panel10PotControl14broadcastValueEi", void, C *, int);
ABI(pr, "_ZN8Presonus5Panel10PotControl12receiveValueEi", void, C *, int);
ABI(fc1, "_ZN8Presonus5Panel12FaderControlC1Ei", void, C *, int);
ABI(fc2, "_ZN8Presonus5Panel12FaderControlC2Ei", void, C *, int);
ABI(fd1, "_ZN8Presonus5Panel12FaderControlD1Ev", void, C *);
ABI(fd0, "_ZN8Presonus5Panel12FaderControlD0Ev", void, C *);
ABI(fk, "_ZN8Presonus5Panel12FaderControl6castToEi", void *, C *, int);
ABI(fb, "_ZN8Presonus5Panel12FaderControl14broadcastValueEi", void, C *, int);
ABI(fr, "_ZN8Presonus5Panel12FaderControl12receiveValueEi", void, C *, int);
ABI(fh, "_ZN8Presonus5Panel12FaderControl11handleTouchEb", void, C *, bool);
extern "C" void potFaderLifecycleEntry(C *, unsigned);
namespace {
void require(bool value) {
  if (!value)
    std::abort();
}
bool tracing = false;
C *tracked = nullptr;
std::size_t trackedSize = 0;
std::vector<C::Timer *> trackedTimers;
std::vector<std::string> events;
P *primary = nullptr, *secondary = nullptr, *tertiary = nullptr;
template <class... T> void emit(const char *kind, T... values) {
  if (!tracing)
    return;
  std::ostringstream out;
  out << kind;
  ((out << ':' << values), ...);
  events.push_back(out.str());
}
unsigned id(P *p) {
  return !p               ? 0
         : p == primary   ? 1
         : p == secondary ? 2
         : p == tertiary  ? 3
                          : 99;
}
void deleting(void *p, std::size_t size = 0) {
  if (!tracing)
    return;
  for (auto it = trackedTimers.begin(); it != trackedTimers.end(); ++it)
    if (*it == p) {
      trackedTimers.erase(it);
      emit("Y");
      break;
    }
  if (p && p == tracked) {
    if (size)
      require(size == trackedSize);
    tracked = nullptr;
    emit("X");
  }
}
std::array<std::uint32_t, 6> state(C &p) {
  return {std::uint32_t(A::lastLevel(p)),
          unsigned(A::parameter(p) != nullptr),
          unsigned(A::altParameter(p) != nullptr),
          unsigned(A::tertiaryParameter(p) != nullptr),
          unsigned(A::io(p) != nullptr),
          std::uint32_t(A::tag(p))};
}
struct Type {
  std::size_t size;
  void (*c1)(C *, int);
  void (*c2)(C *, int);
  void (*d1)(C *);
  void (*d0)(C *);
  void *(*cast)(C *, int);
  void (*broadcast)(C *, int);
  void (*receive)(C *, int);
};
const Type pot{sizeof(Pot), pc1, pc2, pd1, pd0, pk, pb, pr},
    fader{sizeof(Fader), fc1, fc2, fd1, fd0, fk, fb, fr};
void check(C *p, const Type &t, bool isFader) {
  auto **table = *reinterpret_cast<void ***>(p);
  require(table[0] == reinterpret_cast<void *>(t.cast));
  require(table[2] == reinterpret_cast<void *>(t.d1));
  require(table[3] == reinterpret_cast<void *>(t.d0));
  require(table[8] == reinterpret_cast<void *>(t.broadcast));
  require(table[11] == reinterpret_cast<void *>(t.receive));
  require(dynamic_cast<Pot *>(p) != nullptr);
  require((dynamic_cast<Fader *>(p) != nullptr) == isFader);
}
} // namespace
ABI(realDelete, "__real__ZdlPv", void, void *);
ABI(realSizedDelete, "__real__ZdlPvm", void, void *, std::size_t);
ABI(wrapDelete, "__wrap__ZdlPv", void, void *);
ABI(wrapSizedDelete, "__wrap__ZdlPvm", void, void *, std::size_t);
extern "C" void wrapDelete(void *p) {
  deleting(p);
  realDelete(p);
}
extern "C" void wrapSizedDelete(void *p, std::size_t n) {
  deleting(p, n);
  realSizedDelete(p, n);
}
ABI(realD2, "__real__ZN8Presonus5Panel7ControlD2Ev", void, C *);
ABI(wrapD2, "__wrap__ZN8Presonus5Panel7ControlD2Ev", void, C *);
extern "C" void wrapD2(C *p) {
  if (p == tracked)
    emit("D");
  realD2(p);
}
ABI(realRemove,
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE",
    void, P *, Observer *);
ABI(wrapRemove,
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE",
    void, P *, Observer *);
extern "C" void wrapRemove(P *p, Observer *o) {
  emit("R", id(p));
  realRemove(p, o);
}
ABI(realCommand,
    "__real__ZN8presonus13panel_"
    "binding24potFaderParameterCommandERN4Core8Portable9ParameterEjj",
    void, P &, unsigned, std::uint32_t);
ABI(wrapCommand,
    "__wrap__ZN8presonus13panel_"
    "binding24potFaderParameterCommandERN4Core8Portable9ParameterEjj",
    void, P &, unsigned, std::uint32_t);
extern "C" void wrapCommand(P &p, unsigned op, std::uint32_t bits) {
  if (op == 0)
    emit("N", id(&p), bits, 1);
  else
    emit(op == 1 ? "B" : "E", id(&p));
  realCommand(p, op, bits);
}
ABI(realEdit,
    "__real__"
    "ZN8Presonus5Panel16ParamEditHandler15handleParamEditEPN4Core8Portable9Para"
    "meterE",
    void, Handler *, P *);
ABI(wrapEdit,
    "__wrap__"
    "ZN8Presonus5Panel16ParamEditHandler15handleParamEditEPN4Core8Portable9Para"
    "meterE",
    void, Handler *, P *);
extern "C" void wrapEdit(Handler *h, P *p) {
  require(h == &A::paramEdits());
  emit("H", id(p));
  realEdit(h, p);
}
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  return 1000000;
}
int main(int argc, char **argv) {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 1;
  info.defaultValue = 0.25f;
  Core::Portable::NumericParam p(info), second(info), third(info);
  primary = &p;
  secondary = &second;
  tertiary = &third;
  auto &edits = Edits::edits(A::paramEdits());
  require(edits.resize(8));
  if (argc == 2 && std::string(argv[1]) == "--smoke") {
    for (bool isFader : {false, true})
      for (unsigned slot : {2u, 3u}) {
        const auto &type = isFader ? fader : pot;
        auto *v = static_cast<C *>(::operator new(type.size));
        type.c1(v, 7);
        check(v, type, isFader);
        v->setParameter(&p, 0);
        v->setAltParameter(&second);
        v->setTertiaryParameter(&third);
        v->startTimer(0.5f, 123);
        v->startTimer(0.25f, 456);
        require(A::timers().count() == 2);
        trackedTimers = {A::timers().at(0), A::timers().at(1)};
        tracked = v;
        trackedSize = type.size;
        events.clear();
        tracing = true;
        potFaderLifecycleEntry(v, slot);
        require(trackedTimers.empty() && A::timers().count() == 0);
        require((tracked == nullptr) == (slot == 3));
        std::vector<std::string> expected{"D", "Y", "Y", "R:1", "R:2", "R:3"};
        if (slot == 3)
          expected.push_back("X");
        require(events == expected);
        p.changed();
        second.changed();
        third.changed();
        require(events == expected);
        tracing = false;
        if (slot == 2)
          ::operator delete(v);
        tracked = nullptr;
      }
    std::cout << "PASS Pot/Fader actual D1/D0 targets, timer/object deletes, "
                 "three observers and changed-after-lifetime\n";
    return 0;
  }
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line == "quit") {
      std::cout << "OK\n" << std::flush;
      return 0;
    }
    std::istringstream in(line);
    std::string op;
    std::array<std::uint32_t, 6> x{};
    in >> op;
    for (auto &v : x)
      in >> v;
    if (!in)
      return 2;
    bool isFader = op[0] == 'F';
    const auto &type = isFader ? fader : pot;
    std::string action = op.substr(1);
    p.endEdit();
    edits.removeAll();
    if (x[4])
      p.beginEdit();
    if (x[5])
      require(edits.add({&p, 0.}));
    auto *v = static_cast<C *>(::operator new(type.size));
    (action == "C2" ? type.c2 : type.c1)(
        v, int(action == "C1" || action == "C2" ? x[0] : x[3]));
    check(v, type, isFader);
    if (action != "C1" && action != "C2") {
      A::lastLevel(*v) = std::int32_t(x[2]);
      A::parameter(*v) = (x[1] & 1) ? &p : nullptr;
      A::altParameter(*v) = (x[1] & 2) ? &second : nullptr;
      A::tertiaryParameter(*v) = (x[1] & 4) ? &third : nullptr;
    }
    const int oldCount = edits.count();
    events.clear();
    tracked = v;
    trackedSize = type.size;
    tracing = true;
    auto after = state(*v);
    bool ended = false, deleted = false;
    if (action == "D1" || action == "D0") {
      potFaderLifecycleEntry(v, action == "D0" ? 3 : 2);
      ended = true;
      deleted = action == "D0";
      require((tracked == nullptr) == deleted);
    } else {
      if (action == "K")
        emit("K", type.cast(v, int(x[0])) == v ? 1 : 0);
      else if (action == "B")
        type.broadcast(v, int(x[0]));
      else if (action == "R")
        type.receive(v, int(x[0]));
      else if (action == "H" && isFader)
        fh(v, x[0] != 0);
      else if (action != "C1" && action != "C2")
        return 3;
      after = state(*v);
    }
    tracing = false;
    if (isFader && action == "R") {
      require(edits.count() == oldCount + int((x[1] & 1) && !x[4]));
      if (x[1] & 1)
        require(p.isEditing());
    } else
      require(edits.count() == oldCount);
    if (isFader && action == "H" && (x[1] & 1))
      require(p.isEditing() == (x[0] != 0));
    for (unsigned i = 0; i < after.size(); ++i) {
      if (i)
        std::cout << ' ';
      std::cout << after[i];
    }
    std::cout << " |";
    for (auto &e : events)
      std::cout << e << ';';
    std::cout << '\n' << std::flush;
    edits.removeAll();
    p.endEdit();
    if (!ended) {
      A::parameter(*v) = nullptr;
      A::altParameter(*v) = nullptr;
      A::tertiaryParameter(*v) = nullptr;
      type.d1(v);
    }
    if (!deleted)
      ::operator delete(v);
    tracked = nullptr;
  }
}
