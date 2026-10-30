#include "presonus/panel/lcd_display_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <array>
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
  float getValue() const override {
    const float v = NumericParam::getValue();
    if (capture)
      events.push_back("G:" + std::to_string(bits(v)));
    return v;
  }
};
struct IO final : Presonus::Panel::IPanelIO {
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &m) override {
    if (capture)
      events.push_back(
          "W:" + std::to_string(m.bytes[0]) + ":" + std::to_string(m.bytes[1]) +
          ":" + std::to_string(m.bytes[2]) + ":" + std::to_string(m.bytes[3]));
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
  unsigned last, value, disabled, io, display, mode, unused, message, present,
      bound, outlast, outbound, outresult, queueCount, count, resizeCount,
      wantedCapacity, checked = 0;
  const std::array<std::vector<unsigned>, 6> initial = {
      std::vector<unsigned>{}, {}, {1}, {0}, {1, 0}, {1, 2}};
  const int capacities[] = {0, 4, 1, 1, 2, 2};
  while (in >> op >> last >> value >> disabled >> io >> display >> mode >>
         unused >> message >> present >> bound >> outlast >> outbound >>
         outresult >> queueCount) {
    std::vector<unsigned> expectedQueue(queueCount);
    for (auto &n : expectedQueue)
      in >> n;
    in >> count;
    std::vector<std::string> expected(count);
    for (auto &s : expected)
      in >> s;
    in >> resizeCount >> wantedCapacity;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.tag = 1;
    info.minValue = -2147483648.f;
    info.maxValue = 2147483520.f;
    info.defaultValue = op == "P" ? floating(value) : 0;
    Param p(info);
    IO target;
    Presonus::Panel::Control first(11), second(12);
    Presonus::Panel::LCDDisplayControl c(
        presonus::panel::LCDDisplaySourcePort{}, 7, display);
    presonus::panel::ControlAccess::lastLevel(c) = integer(last);
    presonus::panel::ControlAccess::io(c) = io ? &target : nullptr;
    presonus::panel::ControlAccess::parameter(c) =
        present && bound ? &p : nullptr;
    auto &dispatch = presonus::surface_panel_port::ledDispatchState();
    auto &queue = dispatch.dirty;
    const int oldDelta = queue.getDelta();
    queue.resize(0);
    queue.setDelta(1);
    assert(queue.resize(capacities[mode]));
    std::array<Presonus::Panel::Control *, 3> pointers = {&c, &first, &second};
    for (auto index : initial[mode])
      queue.add(pointers[index]);
    dispatch.disabled = disabled;
    events.clear();
    capture = true;
    if (op == "V")
      c.setValue(integer(value));
    else if (op == "T")
      c.transmit();
    else if (op == "P")
      c.paramChanged(present ? &p : nullptr, integer(message));
    else if (op == "K") {
      void *r = c.castTo(integer(value));
      assert((r == &c) == bool(outresult));
      assert(r == nullptr || r == &c);
    } else
      return 3;
    capture = false;
    std::vector<unsigned> actualQueue;
    for (int i = 0; i < queue.count(); ++i) {
      unsigned k = 0;
      while (k < 3 && pointers[k] != queue.at(i))
        ++k;
      assert(k < 3);
      actualQueue.push_back(k);
    }
    const bool okay =
        static_cast<unsigned>(presonus::panel::ControlAccess::lastLevel(c)) ==
            outlast &&
        unsigned(presonus::panel::ControlAccess::parameter(c) != nullptr) ==
            outbound &&
        events == expected && actualQueue == expectedQueue &&
        queue.getCapacity() == int(wantedCapacity);
    queue.resize(0);
    queue.setDelta(oldDelta);
    dispatch.disabled = 0;
    if (!okay) {
      std::cerr << "case " << checked << " mismatch\n";
      for (auto &s : events)
        std::cerr << s << ' ';
      return 4;
    }
    ++checked;
  }
  if (checked != 11288)
    return 5;
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"all_IO_captured\":true,\"real_shared_queue\":true}\n";
}
