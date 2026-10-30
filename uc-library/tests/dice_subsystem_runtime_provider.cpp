#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include "presonus/surface_panel/OutputPin.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

extern "C" __attribute__((noinline)) void
dice_control_inherited_post(Presonus::DICE::SysexReceiver *receiver,
                            Presonus::DICE::SysexPacket *packet) {
  receiver->post(*packet);
}

namespace {
void check(bool b) {
  if (!b)
    std::abort();
}
Presonus::DICE::Dice3Subsystem *registered = nullptr;
unsigned posts = 0, idles = 0;
class PinIO final : public presonus::surface_panel_port::OutputPinIO {
public:
  unsigned opens = 0, closes = 0, pinPrints = 0;
  std::map<std::FILE *, bool> live;
  std::vector<int> values;
  std::FILE *open(const char *path, const char *mode) override {
    check(std::strcmp(mode, "a") == 0);
    const std::string p(path);
    check(p == "/sys/class/gpio/export" ||
          p == "/sys/class/gpio/gpio100/direction" ||
          p == "/sys/class/gpio/gpio100/value");
    auto *f = reinterpret_cast<std::FILE *>(
        std::uintptr_t(0x30000000 + 16 * ++opens));
    live[f] = true;
    return f;
  }
  int printPin(std::FILE *f, const char *format, int pin) override {
    check(live[f] && std::strcmp(format, "%d") == 0 && pin == 100);
    ++pinPrints;
    return 3;
  }
  int close(std::FILE *f) override {
    check(live[f]);
    live[f] = false;
    ++closes;
    return 0;
  }
  void formatPath(char *out, std::size_t n, const char *format,
                  int pin) override {
    check(pin == 100);
    const int r = std::snprintf(out, n, format, pin);
    check(r > 0 && static_cast<std::size_t>(r) < n);
  }
  std::size_t write(const void *p, std::size_t n, std::size_t count,
                    std::FILE *f) override {
    check(live[f] && n == 1 && count == 3 && std::memcmp(p, "out", 3) == 0);
    return count;
  }
  int buffering(std::FILE *f, char *, int mode, std::size_t n) override {
    check(live[f] && mode == 2 && n == 0);
    return 0;
  }
  int put(int c, std::FILE *f) override {
    check(live[f] && (c == '0' || c == '1'));
    values.push_back(c);
    return c;
  }
  int error() override { std::abort(); }
  void log(const char *) override { std::abort(); }
  void logSet(const char *, int, int) override { std::abort(); }
  void allClosed() {
    check(opens == closes);
    for (const auto &x : live)
      check(!x.second);
  }
};
} // namespace
extern "C" std::FILE *__wrap_fopen(const char *, const char *) { std::abort(); }
extern "C" int __wrap_fclose(std::FILE *) { std::abort(); }
extern "C" int __wrap_open(const char *, int, ...) { std::abort(); }
extern "C" int __wrap___open_2(const char *, int) { std::abort(); }
extern "C" int __wrap_close(int) { std::abort(); }
extern "C" int __wrap_ioctl(int, unsigned long, ...) { std::abort(); }
extern "C" void
__real__ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE(
    Presonus::DICE::Dice3Uart *, Presonus::DICE::ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE(
    Presonus::DICE::Dice3Uart *u, Presonus::DICE::ISysexReceiver *r) {
  registered = dynamic_cast<Presonus::DICE::Dice3Subsystem *>(r);
  check(registered != nullptr);
  __real__ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE(
      u, r);
}
extern "C" void __wrap__ZN8Presonus4DICE9Dice3Uart4postERNS0_11SysexPacketE(
    Presonus::DICE::Dice3Uart *, Presonus::DICE::SysexPacket *p) {
  check(registered != nullptr);
  if (posts++ == 0) {
    const unsigned char expected[] = {0xf0, 9, 0x40, 0, 0, 0,    0,
                                      0x40, 0, 0,    0, 0, 0xa5, 0xf7};
    check(p->length == 14 && std::memcmp(p->bytes.data(), expected, 14) == 0);
  } else
    check(p->length == 2 && p->bytes[1] == 22);
}
extern "C" void
__wrap__ZN8Presonus4DICE9Dice3Uart6onIdleEv(Presonus::DICE::Dice3Uart *) {
  check(registered != nullptr);
  ++idles;
  registered->portableState().command = 255;
  registered->portableState().status = 1;
}
int main() {
  bool caught = false;
  try {
    Presonus::DICE::Dice3Subsystem missing;
  } catch (const std::logic_error &) {
    caught = true;
  }
  check(caught && registered == nullptr);
  PinIO io;
  presonus::dice::LinuxProgrammerDeviceServices device(&io);
  presonus::dice::CclSubsystemRuntime runtime(device);
  auto &uart = Presonus::DICE::Dice3Uart::instance();
  auto &state = presonus::dice::UartLifetimeAccess::state(uart);
  const auto before = state.receivers.count();
  {
    presonus::dice::ScopedSubsystemRuntime scope(runtime);
    {
      Presonus::DICE::Dice3Subsystem s;
      check(registered == &s && state.receivers.count() == before + 1);
      io.allClosed();
      check(s.portableResponseWord() == 0 &&
            s.portableState().infoWords[0] == 0xffffffffU);
      check(s.programSerialData(0x80000000U, 0xa5) == 0 && idles == 1);
      s.resetDice3();
      io.allClosed();
      s.portableResponseWord() = 123;
      s.portableState().infoWords[0] = 0xaabbccdd;
      Presonus::DICE::SysexPacket packet;
      packet.length = 2;
      packet.bytes[1] = 22;
      Presonus::DICE::SysexReceiver *base = &s;
      dice_control_inherited_post(base, &packet);
      check(s.portableResponseWord() == 0 &&
            s.portableState().infoWords[0] == 0xaabbccdd &&
            s.portableState().command == 0 && s.portableState().status == 0);
    }
    check(state.receivers.count() == before + 1);
  }
  caught = false;
  try {
    Presonus::DICE::Dice3Subsystem missing;
  } catch (const std::logic_error &) {
    caught = true;
  }
  check(caught);
  check(posts == 2 && io.pinPrints == 2 && io.opens == 6 && io.closes == 6 &&
        io.values == std::vector<int>({'0', '1', '0', '1'}));
  std::cout << "PASS actual CCL runtime/clock/sleep, Linux GPIO adapter "
               "through intercepted IO, real UART registration, raw post/idle "
               "boundaries, inherited acknowledgement/post and no unregister; "
               "zero physical device effects\n";
}
