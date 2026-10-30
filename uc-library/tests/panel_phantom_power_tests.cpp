#include "presonus/panel/phantom_power_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
namespace {
bool capture = false;
std::vector<std::string> events;
unsigned bits(float f) {
  unsigned u;
  std::memcpy(&u, &f, 4);
  return u;
}
float floating(unsigned u) {
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}
int integer(unsigned u) {
  int i;
  std::memcpy(&i, &u, 4);
  return i;
}
struct Param final : Core::Portable::NumericParam {
  using NumericParam::NumericParam;
  float getNormalized() const override {
    const float v = NumericParam::getNormalized();
    if (capture)
      events.push_back("N:" + std::to_string(bits(v)));
    return v;
  }
};
struct IO final : Presonus::Panel::IPanelIO {
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &m) override {
    if (capture)
      events.push_back("W:" + std::to_string(m.bytes[0]) + ":" +
                       std::to_string(m.bytes[1]) + ":" +
                       std::to_string(m.bytes[2]));
    return -17;
  }
  int broadcast(Presonus::Panel::Control *) override { std::abort(); }
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
};
} // namespace
extern "C" void
realRemove(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrappedRemove(
    Core::Portable::Parameter *,
    Core::Portable::IParamObserver
        *) asm("__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
               "14IParamObserverE");
extern "C" void wrappedRemove(Core::Portable::Parameter *p,
                              Core::Portable::IParamObserver *o) {
  if (capture)
    events.push_back("R");
  realRemove(p, o);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  if (!in)
    return 2;
  std::string op;
  unsigned last, value, disabled, io, tag, wanted, ignored, message, present,
      bound, outlast, outdisabled, outbound, count, checked = 0;
  while (in >> op >> last >> value >> disabled >> io >> tag >> wanted >>
         ignored >> message >> present >> bound >> outlast >> outdisabled >>
         outbound >> count) {
    std::vector<std::string> expected(count);
    for (auto &s : expected)
      in >> s;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.tag = 1;
    info.minValue = 0;
    info.maxValue = 1;
    info.defaultValue = op == "P" ? floating(value) : 0;
    Param p(info);
    IO target;
    Presonus::Panel::PhantomPowerControl c(presonus::panel::PhantomSourcePort{},
                                           integer(tag));
    c.disableControl(disabled != 0, false);
    presonus::panel::ControlAccess::lastLevel(c) = integer(last);
    presonus::panel::ControlAccess::io(c) = io ? &target : nullptr;
    presonus::panel::ControlAccess::parameter(c) =
        present && bound ? &p : nullptr;
    events.clear();
    capture = true;
    if (op == "B")
      c.broadcastValue(integer(value));
    else if (op == "T")
      c.transmit();
    else if (op == "D")
      c.disableControl(wanted != 0, ignored != 0);
    else if (op == "P")
      c.paramChanged(present ? &p : nullptr, integer(message));
    else
      return 3;
    capture = false;
    if (static_cast<unsigned>(presonus::panel::ControlAccess::lastLevel(c)) !=
            outlast ||
        unsigned(presonus::panel::PhantomAccess::disabled(c)) != outdisabled ||
        unsigned(presonus::panel::ControlAccess::parameter(c) != nullptr) !=
            outbound ||
        events != expected) {
      std::cerr << "case " << checked << " mismatch\n";
      for (auto &s : events)
        std::cerr << s << ' ';
      return 4;
    }
    ++checked;
  }
  if (checked != 4384)
    return 5;
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"all_IO_captured\":true}\n";
}
