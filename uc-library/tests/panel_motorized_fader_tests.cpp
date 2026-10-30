#include "presonus/panel/motorized_fader_control.hpp"
#include "presonus/panel/param_edit_handler.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <new>
#include <string>
#include <vector>
using M = Presonus::Panel::MotorizedFaderControl;
using A = presonus::panel::ControlAccess;
using X = presonus::panel::MotorizedFaderAccess;
extern "C" void mc1(M *,
                    int) asm("_ZN8Presonus5Panel21MotorizedFaderControlC1Ei");
extern "C" void mc2(M *,
                    int) asm("_ZN8Presonus5Panel21MotorizedFaderControlC2Ei");
extern "C" void md1(M *) asm("_ZN8Presonus5Panel21MotorizedFaderControlD1Ev");
extern "C" void md0(M *) asm("_ZN8Presonus5Panel21MotorizedFaderControlD0Ev");
namespace {
void *tracked = nullptr;
int deallocated = 0;
class CaptureIO final : public Presonus::Panel::IPanelIO {
public:
  std::vector<std::array<unsigned char, 4>> packets;
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &m) override {
    packets.push_back(m.bytes);
    char encoded[128]{};
    int count = uart_protocol_encode(&m, encoded);
    if (count <= 0)
      std::abort();
    return -17; // Original caller ignores the real port's result.
  }
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
};
int signedBits(std::uint32_t bits) {
  int value;
  std::memcpy(&value, &bits, 4);
  return value;
}
std::array<std::uint32_t, 8> state(M &v) {
  return {static_cast<std::uint32_t>(A::lastLevel(v)),
          unsigned(v.getParameter() != nullptr),
          unsigned(A::io(v) != nullptr),
          static_cast<std::uint32_t>(A::tag(v)),
          X::receiving(v),
          X::touched(v),
          static_cast<std::uint32_t>(X::lastInput(v)),
          static_cast<unsigned>(
              presonus::panel::motorizedDeferredControls().count())};
}
} // namespace
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *p) {
  if (p == tracked)
    ++deallocated;
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t size) {
  if (p == tracked)
    ++deallocated;
  __real__ZdlPvm(p, size);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string op;
  std::uint32_t arg, level, tag, last, bits;
  int present, original, receiving, touched, disabled, queued, message;
  unsigned cases = 0, realDeletes = 0;
  while (input >> op >> arg >> present >> original >> level >> tag >>
         receiving >> touched >> last >> disabled >> queued >> bits >>
         message) {
    std::array<std::uint32_t, 8> expected;
    for (auto &value : expected)
      input >> value;
    unsigned packetCount;
    input >> packetCount;
    std::vector<std::array<unsigned char, 4>> packets;
    for (unsigned i = 0; i < packetCount; ++i) {
      std::array<unsigned char, 4> packet;
      for (auto &value : packet) {
        unsigned n;
        input >> n;
        value = n;
      }
      packets.push_back(packet);
    }
    int expectedDelete, expectedCast;
    input >> expectedDelete >> expectedCast;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.minValue = op == "H" ? -1024.f : 0.f;
    info.maxValue = op == "H" ? 1024.f : 1.f;
    Core::Portable::NumericParam parameter(info);
    Core::Portable::AliasParam alias(info);
    if (original)
      alias.setOriginal(&parameter);
    float value;
    std::memcpy(&value, &bits, 4);
    if (op == "P")
      parameter.setNormalized(value, false);
    else if (op == "H")
      parameter.setValue(value, false);
    CaptureIO io;
    void *storage = ::operator new(sizeof(M));
    M *control = static_cast<M *>(storage);
    if (op == "C2")
      mc2(control, signedBits(arg));
    else
      mc1(control, signedBits(op == "C1" ? arg : tag));
    auto &dispatch = presonus::surface_panel_port::ledDispatchState();
    dispatch.dirty.removeAll();
    dispatch.disabled = disabled;
    if (queued)
      dispatch.dirty.add(control);
    if (op != "C1" && op != "C2") {
      A::parameter(*control) =
          present == 0   ? nullptr
          : present == 1 ? static_cast<Core::Portable::Parameter *>(&parameter)
                         : static_cast<Core::Portable::Parameter *>(&alias);
      A::io(*control) = &io;
      A::lastLevel(*control) = signedBits(level);
      X::receiving(*control) = receiving;
      X::touched(*control) = touched;
      X::lastInput(*control) = signedBits(last);
    }
    auto actual = state(*control);
    tracked = control;
    deallocated = 0;
    int cast = -1;
    if (op == "D1")
      md1(control);
    else if (op == "D0")
      md0(control);
    else {
      if (op == "K")
        cast = control->castTo(signedBits(arg)) == control;
      else if (op == "P")
        control->paramChanged(&parameter, message);
      else if (op == "B")
        control->broadcastValue(signedBits(arg));
      else if (op == "T")
        control->transmit();
      else if (op == "R")
        control->receiveValue(signedBits(arg));
      else if (op == "H")
        control->handleTouch(arg != 0);
      actual = state(*control);
    }
    if (actual != expected || io.packets != packets ||
        deallocated != expectedDelete || cast != expectedCast) {
      std::cerr << "case " << cases << ' ' << op << " mismatch\n";
      for (auto v : actual)
        std::cerr << v << ' ';
      std::cerr << " expected ";
      for (auto v : expected)
        std::cerr << v << ' ';
      std::cerr << '\n';
      return 3;
    }
    realDeletes += deallocated;
    tracked = nullptr;
    dispatch.dirty.removeAll();
    dispatch.disabled = 0;
    auto &edits = A::paramEdits();
    presonus::panel::ParamEditHandlerAccess::edits(edits).removeAll();
    presonus::panel::ParamEditHandlerAccess::blockers(edits).removeAll();
    if (op == "D1")
      ::operator delete(storage);
    else if (op != "D0")
      delete control;
    ++cases;
  }
  if (cases != 306 || realDeletes != 1)
    std::abort();
  std::cout << "{\"passed\":true,\"cases\":" << cases
            << ",\"actual_D0_deletes\":" << realDeletes << "}\n";
}
