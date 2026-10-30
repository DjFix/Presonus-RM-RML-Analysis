#include "presonus/panel/blink_led_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <string>
#include <vector>
using E = Presonus::Panel::BlinkLEDControl;
using S = Presonus::Panel::SwitchControl;
using L = Presonus::Panel::LEDControl;
using A = presonus::panel::ControlAccess;
using X = presonus::panel::BlinkLEDAccess;
namespace {
bool capture = false;
std::vector<std::string> events;
void *tracked = nullptr;
unsigned frees = 0;
void emit(std::string v) {
  if (capture)
    events.push_back(v);
}
float floating(unsigned v) {
  float x;
  std::memcpy(&x, &v, 4);
  return x;
}
unsigned bits(float v) {
  unsigned x;
  std::memcpy(&x, &v, 4);
  return x;
}
int integer(unsigned v) {
  int x;
  std::memcpy(&x, &v, 4);
  return x;
}
class Probe : public E {
public:
  Probe() : E(7, 7, false) {}
  void broadcastValue(int value) override {
    emit("B:" + std::to_string(static_cast<unsigned>(value)));
  }
};
class Param : public Core::Portable::NumericParam {
public:
  using NumericParam::NumericParam;
  mutable unsigned index = 0;
  unsigned values[3]{};
  float getValue() const override {
    const float v = floating(values[index < 3 ? index++ : 2]);
    auto &self = *const_cast<Param *>(this);
    self.NumericParam::setValue(v, false);
    const float actual = NumericParam::getValue();
    emit("G:" + std::to_string(bits(actual)));
    return actual;
  }
};
class IO : public Presonus::Panel::IPanelIO {
public:
  int readMsg(Uart_Msg_Type &) override { return 0; }
  int writeMsg(Uart_Msg_Type &m) override {
    std::string v = "W";
    for (auto b : m.bytes)
      v += ":" + std::to_string(b);
    emit(v);
    return -17;
  }
  int open(const char *) override { return 0; }
  void close() override {}
  int enableHISpeed(bool) override { return 0; }
};
} // namespace
extern "C" void
realC(S *, int, int,
      bool) asm("__real__ZN8Presonus5Panel13SwitchControlC2Eiib");
extern "C" void
wrapC(S *v, int tag, int group,
      bool immediate) asm("__wrap__ZN8Presonus5Panel13SwitchControlC2Eiib");
extern "C" void wrapC(S *v, int tag, int group, bool immediate) {
  emit("C:" + std::to_string(static_cast<unsigned>(tag)) + ":" +
       std::to_string(static_cast<unsigned>(group)) + ":" +
       std::to_string(immediate));
  realC(v, tag, group, immediate);
}
extern "C" void realD(S *) asm("__real__ZN8Presonus5Panel13SwitchControlD2Ev");
extern "C" void wrapD(S *v) asm("__wrap__ZN8Presonus5Panel13SwitchControlD2Ev");
extern "C" void wrapD(S *v) {
  emit("D");
  realD(v);
}
// Explicit inherited-app boundary fixture. Production links genuine LED body;
// separate retained LED proofs establish it. No production stub is introduced.
extern "C" void wrapL(L *, Core::Portable::Parameter *, int m) asm(
    "__wrap__"
    "ZN8Presonus5Panel10LEDControl12paramChangedEPN4Core8Portable9ParameterEi");
extern "C" void wrapL(L *, Core::Portable::Parameter *, int m) {
  emit("L:" + std::to_string(static_cast<unsigned>(m)));
}
extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void wrapDelete(void *v) asm("__wrap__ZdlPv");
extern "C" void wrapDelete(void *v) {
  if (v == tracked && capture) {
    emit("X");
    ++frees;
  }
  realDelete(v);
}
extern "C" void realDeleteSized(void *, std::size_t) asm("__real__ZdlPvm");
extern "C" void wrapDeleteSized(void *v, std::size_t n) asm("__wrap__ZdlPvm");
extern "C" void wrapDeleteSized(void *v, std::size_t n) {
  if (v == tracked && capture) {
    emit("X");
    ++frees;
  }
  realDeleteSized(v, n);
}
extern "C" void c1(E *, int, int,
                   bool) asm("_ZN8Presonus5Panel15BlinkLEDControlC1Eiib");
extern "C" void c2(E *, int, int,
                   bool) asm("_ZN8Presonus5Panel15BlinkLEDControlC2Eiib");
extern "C" void d1(E *) asm("_ZN8Presonus5Panel15BlinkLEDControlD1Ev");
extern "C" void d0(E *) asm("_ZN8Presonus5Panel15BlinkLEDControlD0Ev");
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  std::string op;
  unsigned arg, message, primary, alt, tertiary, cache, sync, r0, r1, r2, group,
      immediate, expectedSync, count;
  unsigned checked = 0, deletes = 0;
  while (in >> op >> arg >> message >> primary >> alt >> tertiary >> cache >>
         sync >> r0 >> r1 >> r2 >> group >> immediate >> expectedSync >>
         count) {
    std::vector<std::string> wanted(count);
    for (auto &v : wanted)
      in >> v;
    int expectedCast;
    in >> expectedCast;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = -1;
    info.maxValue = 10000000;
    Param parameter(info);
    parameter.values[0] = r0;
    parameter.values[1] = r1;
    parameter.values[2] = r2;
    IO io;
    E *v = nullptr;
    bool ctor = op == "C1" || op == "C2";
    events.clear();
    frees = 0;
    if (ctor) {
      void *storage = ::operator new(sizeof(E));
      v = static_cast<E *>(storage);
      capture = true;
      if (op == "C1")
        c1(v, integer(arg), integer(group), immediate != 0);
      else
        c2(v, integer(arg), integer(group), immediate != 0);
      capture = false;
    } else {
      v = (op == "P") ? static_cast<E *>(new Probe) : new E(7, 7, false);
      A::lastLevel(*v) = integer(cache);
      A::parameter(*v) = primary ? &parameter : nullptr;
      A::altParameter(*v) = alt ? &parameter : nullptr;
      A::tertiaryParameter(*v) = tertiary ? &parameter : nullptr;
      A::io(*v) = &io;
      X::resynchronize(*v) = sync;
    }
    tracked = v;
    int actualCast = -1;
    unsigned actualSync = X::resynchronize(*v);
    capture = true;
    if (op == "P")
      v->paramChanged(&parameter, integer(message));
    else if (op == "T")
      v->transmitBlinkRate(floating(arg));
    else if (op == "K")
      actualCast = v->castTo(integer(arg)) == v;
    else if (op == "D1")
      d1(v);
    else if (op == "D0")
      d0(v);
    if (op != "D1" && op != "D0")
      actualSync = X::resynchronize(*v);
    capture = false;
    if (events != wanted || actualSync != expectedSync ||
        actualCast != expectedCast || frees != (op == "D0" ? 1U : 0U)) {
      std::cerr << "case " << checked << ' ' << op << " sync " << actualSync
                << " expected " << expectedSync << " events ";
      for (auto &s : events)
        std::cerr << s << ' ';
      std::cerr << " wanted ";
      for (auto &s : wanted)
        std::cerr << s << ' ';
      std::cerr << '\n';
      return 3;
    }
    deletes += frees;
    tracked = nullptr;
    if (op == "D1")
      ::operator delete(v);
    else if (op != "D0") {
      A::parameter(*v) = nullptr;
      A::altParameter(*v) = nullptr;
      A::tertiaryParameter(*v) = nullptr;
      delete v;
    }
    ++checked;
  }
  if (checked != 1024 || deletes != 1)
    std::abort();
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"actual_D0_deletes\":" << deletes << "}\n";
}
