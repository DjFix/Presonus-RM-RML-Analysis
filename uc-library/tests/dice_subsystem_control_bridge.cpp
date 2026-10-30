#include "presonus/dice/manager.hpp"
#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>
#include <type_traits>
#include <vector>

extern "C" __attribute__((noinline)) bool
dice_control_interface_accepts(Presonus::DICE::ISysexReceiver *receiver,
                               const Presonus::DICE::SysexPacket *packet) {
  return receiver->accepts(*packet);
}
extern "C" __attribute__((noinline)) void
dice_control_interface_receive(Presonus::DICE::ISysexReceiver *receiver,
                               const Presonus::DICE::SysexPacket *packet) {
  receiver->receive(*packet);
}

using Subsystem = Presonus::DICE::Dice3Subsystem;
using Uart = Presonus::DICE::Dice3Uart;
namespace {
void check(bool b) {
  if (!b)
    std::abort();
}
struct Input {
  std::string kind;
  unsigned lazy, unit, ack, status, command, initialStatus;
  std::uint32_t serial, infoResult, responseWord;
  std::int64_t ticks[2];
  std::array<std::uint32_t, 5> seed;
} current;
bool active = false, expectAllocation = false, phaseVptr = false;
Subsystem *currentSubsystem = nullptr;
unsigned clockIndex = 0, c1calls = 0, c2calls = 0, d1calls = 0, d2calls = 0,
         registered = 0;
std::vector<std::string> events;
extern "C" void *_ZTVN8Presonus4DICE14Dice3SubsystemE[];
std::uintptr_t vptr(const void *p) {
  std::uintptr_t v;
  std::memcpy(&v, p, sizeof(v));
  return v;
}
bool subsystemVptr(const void *p) {
  return vptr(p) == reinterpret_cast<std::uintptr_t>(
                        _ZTVN8Presonus4DICE14Dice3SubsystemE + 2);
}
void event(const char *kind) {
  events.push_back(std::string("{\"kind\":\"") + kind + "\"}");
}
std::int32_t signedWord(std::uint32_t w) {
  std::int32_t s;
  std::memcpy(&s, &w, 4);
  return s;
}
std::string hex(const unsigned char *p, std::size_t n) {
  static constexpr char d[] = "0123456789abcdef";
  std::string s;
  for (std::size_t i = 0; i < n; ++i) {
    s += d[p[i] >> 4];
    s += d[p[i] & 15];
  }
  return s;
}
class Pin final : public presonus::dice::ProgrammerOutputPin {
public:
  Pin() { events.push_back("{\"kind\":\"pin_construct\",\"number\":100}"); }
  ~Pin() override { event("pin_destroy"); }
  void set(int value) override {
    check(value == 0 || value == 1);
    events.push_back(
        "{\"kind\":\"pin_set\",\"value\":" + std::to_string(value) + "}");
  }
};
class Runtime final : public presonus::dice::SubsystemRuntime,
                      public presonus::dice::SubsystemServices {
public:
  Uart *uart = nullptr;
  void bind(Subsystem &s, Uart &u) override {
    uart = &u;
    s.setPortableServices(*this);
    s.setPortableRuntime(*this);
  }
  std::unique_ptr<presonus::dice::ProgrammerOutputPin> makeResetPin() override {
    return std::make_unique<Pin>();
  }
  void sleepMilliseconds(std::uint32_t ms) override {
    check(ms == 1 || ms == 2000);
    events.push_back(
        "{\"kind\":\"sleep\",\"milliseconds\":" + std::to_string(ms) + "}");
  }
  void post(Presonus::DICE::SysexPacket &p) override {
    check(p.length == 14);
    const auto &m = p.portableMetadata();
    check(m.headerWords == std::array<std::uint32_t, 2>{} &&
          m.trailingWords == std::array<std::uint32_t, 4>{});
    events.push_back("{\"kind\":\"post\",\"data\":\"" +
                     hex(p.bytes.data(), 14) +
                     "\",\"length\":14,\"quotient\":" +
                     std::to_string(m.constructedQuotient) + "}");
  }
  std::uint32_t waitAck(Subsystem &s, std::int64_t timeout) override {
    check(timeout == 500);
    events.push_back("{\"kind\":\"ack\",\"timeout\":500}");
    s.portableState().status = static_cast<unsigned char>(current.status);
    return current.ack;
  }
};
class Routes final : public presonus::dice::RouteSink {
public:
  std::int32_t setRoute(const presonus::dice::RouteTuple &) override {
    std::abort();
  }
};
class ManagerRuntime final : public presonus::dice::ManagerServices {
public:
  std::int64_t clockRawTicks() override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void terminateThread() override { std::abort(); }
};
struct UartAccess : Uart {
  static void forget() { theInstance = nullptr; }
};
struct Derived : Subsystem {
  Derived() : Subsystem() {}
  explicit Derived(presonus::dice::BorrowedSubsystemSetup tag)
      : Subsystem(tag) {}
};
void seed(Subsystem &s) {
  auto &v = s.portableState();
  v.command = static_cast<unsigned char>(current.command);
  v.status = static_cast<unsigned char>(current.initialStatus);
  v.infoWords = {current.seed[0], current.seed[1], current.seed[2]};
  v.rateWord = current.seed[3];
  v.clockWord = current.seed[4];
  s.portableResponseWord() = current.responseWord;
}
std::string stateJson(const presonus::dice::SubsystemState &s,
                      std::uint32_t response) {
  return "{\"command\":" + std::to_string(s.command) +
         ",\"status\":" + std::to_string(s.status) +
         ",\"response_word\":" + std::to_string(response) + ",\"info\":[" +
         std::to_string(s.infoWords[0]) + "," + std::to_string(s.infoWords[1]) +
         "," + std::to_string(s.infoWords[2]) +
         "],\"rate\":" + std::to_string(s.rateWord) +
         ",\"clock\":" + std::to_string(s.clockWord) + "}";
}
void dispatchCheck(Subsystem &s) {
  Presonus::DICE::SysexPacket p;
  p.length = 2;
  p.bytes[1] = 1;
  Presonus::DICE::ISysexReceiver *interface = &s;
  check(dynamic_cast<Subsystem *>(interface) == &s &&
        dice_control_interface_accepts(interface, &p));
  p.bytes[2] = 7;
  dice_control_interface_receive(interface, &p);
  check(s.portableState().command == 1 && s.portableState().status == 7);
  Presonus::DICE::SysexReceiver *base = &s;
  check(static_cast<Presonus::DICE::ISysexReceiver *>(base) == interface);
}
} // namespace
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  check(clockIndex < 2);
  auto t = current.ticks[clockIndex++];
  events.push_back("{\"kind\":\"clock\",\"value\":" + std::to_string(t) + "}");
  return t;
}
} // namespace presonus::dice
extern "C" void *__real__Znwm(std::size_t);
extern "C" void *__wrap__Znwm(std::size_t size) {
  const bool capture = active && expectAllocation;
  if (capture) {
    expectAllocation = false;
    check(size == sizeof(Uart));
  }
  void *p = __real__Znwm(size);
  if (capture)
    event("allocate_uart");
  return p;
}
extern "C" void __real__ZN8Presonus4DICE9Dice3UartC2Ev(Uart *);
extern "C" void __wrap__ZN8Presonus4DICE9Dice3UartC2Ev(Uart *p) {
  if (active)
    event("construct_uart");
  __real__ZN8Presonus4DICE9Dice3UartC2Ev(p);
}
extern "C" void __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *);
extern "C" void __wrap__ZN4Core8Portable9Deletable11addInstanceEPS1_(
    Core::Portable::Deletable *p) {
  if (active)
    event("register_deletable");
  __real__ZN4Core8Portable9Deletable11addInstanceEPS1_(p);
}
extern "C" void
__real__ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE(
    Uart *, Presonus::DICE::ISysexReceiver *);
extern "C" void
__wrap__ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE(
    Uart *u, Presonus::DICE::ISysexReceiver *r) {
  check(active && dynamic_cast<Subsystem *>(r) != nullptr);
  ++registered;
  events.push_back("{\"kind\":\"register_receiver\",\"receiver_this\":true}");
  check(subsystemVptr(dynamic_cast<Subsystem *>(r)));
  __real__ZN8Presonus4DICE9Dice3Uart16registerReceiverEPNS0_14ISysexReceiverE(
      u, r);
}
extern "C" void __real__ZN8Presonus4DICE14Dice3SubsystemC1Ev(Subsystem *);
extern "C" void __real__ZN8Presonus4DICE14Dice3SubsystemC2Ev(Subsystem *);
extern "C" void __wrap__ZN8Presonus4DICE14Dice3SubsystemC1Ev(Subsystem *p) {
  ++c1calls;
  __real__ZN8Presonus4DICE14Dice3SubsystemC1Ev(p);
  phaseVptr = subsystemVptr(p);
}
extern "C" void __wrap__ZN8Presonus4DICE14Dice3SubsystemC2Ev(Subsystem *p) {
  ++c2calls;
  __real__ZN8Presonus4DICE14Dice3SubsystemC2Ev(p);
  phaseVptr = subsystemVptr(p);
}
extern "C" void __real__ZN8Presonus4DICE14Dice3SubsystemD1Ev(Subsystem *);
extern "C" void __real__ZN8Presonus4DICE14Dice3SubsystemD2Ev(Subsystem *);
extern "C" void __wrap__ZN8Presonus4DICE14Dice3SubsystemD1Ev(Subsystem *p) {
  ++d1calls;
  __real__ZN8Presonus4DICE14Dice3SubsystemD1Ev(p);
}
extern "C" void __wrap__ZN8Presonus4DICE14Dice3SubsystemD2Ev(Subsystem *p) {
  ++d2calls;
  __real__ZN8Presonus4DICE14Dice3SubsystemD2Ev(p);
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE12Dice3Manager12getDice3InfoEPNS0_8DiceInfoE(
    Presonus::DICE::Dice3Manager *, Presonus::DICE::DiceInfo *p) {
  check(p != nullptr && currentSubsystem != nullptr &&
        currentSubsystem->portableState().infoWords[0] == 0xffffffffU);
  event("invalidate");
  event("info");
  return signedWord(current.infoResult);
}

int main() {
  static_assert(std::is_abstract_v<Presonus::DICE::SysexReceiver>);
  static_assert(std::is_base_of_v<Presonus::DICE::ISysexReceiver, Subsystem>);
  events.reserve(64);
  while (std::cin >> current.kind >> current.lazy >> current.serial >>
         current.unit >> current.ack >> current.status >> current.ticks[0] >>
         current.ticks[1] >> current.infoResult >> current.seed[0] >>
         current.seed[1] >> current.seed[2] >> current.seed[3] >>
         current.seed[4] >> current.command >> current.initialStatus >>
         current.responseWord) {
    active = false;
    Runtime runtime;
    presonus::dice::ScopedSubsystemRuntime context(runtime);
    auto &uart = Uart::instance();
    if (current.lazy)
      UartAccess::forget();
    events.clear();
    clockIndex = 0;
    phaseVptr = false;
    expectAllocation = current.lazy != 0;
    active = true;
    std::string result = "null";
    presonus::dice::SubsystemState after;
    std::uint32_t response = 0;
    bool vtable = true;
    if (current.kind == "c1") {
      Subsystem s;
      after = s.portableState();
      response = s.portableResponseWord();
      vtable = phaseVptr;
      dispatchCheck(s);
    } else if (current.kind == "c2") {
      Derived s;
      after = s.portableState();
      response = s.portableResponseWord();
      vtable = phaseVptr;
      dispatchCheck(s);
    } else if (current.kind == "d1" || current.kind == "d2") {
      alignas(Derived) unsigned char storage[sizeof(Derived)];
      Subsystem *s =
          current.kind == "d1"
              ? new (storage)
                    Subsystem(presonus::dice::BorrowedSubsystemSetup{})
              : static_cast<Subsystem *>(new (storage) Derived(
                    presonus::dice::BorrowedSubsystemSetup{}));
      seed(*s);
      auto *state = &s->portableState();
      auto *word = &s->portableResponseWord();
      const unsigned oldRegistered = registered;
      const auto oldEvents = events.size();
      if (current.kind == "d1")
        s->~Subsystem();
      else
        static_cast<Derived *>(s)->~Derived();
      std::memcpy(&after, state, sizeof(after));
      std::memcpy(&response, word, sizeof(response));
      check(registered == oldRegistered && events.size() == oldEvents);
    } else {
      Subsystem s(presonus::dice::BorrowedSubsystemSetup{});
      runtime.bind(s, uart);
      seed(s);
      currentSubsystem = &s;
      Routes routes;
      ManagerRuntime managerRuntime;
      Presonus::DICE::Dice3Manager manager(routes);
      manager.setPortableRuntime(s, uart, managerRuntime);
      if (current.kind == "reset")
        s.resetDice3();
      else if (current.kind == "serial")
        result = std::to_string(static_cast<std::uint32_t>(s.programSerialData(
            current.serial, static_cast<unsigned char>(current.unit))));
      else if (current.kind == "mserial")
        result = std::to_string(static_cast<std::uint32_t>(
            manager.setDice3Serial(signedWord(current.serial),
                                   static_cast<unsigned char>(current.unit))));
      else {
        check(current.kind == "mreset");
        result =
            std::to_string(static_cast<std::uint32_t>(manager.resetDice3()));
      }
      after = s.portableState();
      response = s.portableResponseWord();
      vtable = subsystemVptr(&s);
    }
    active = false;
    check(!expectAllocation || !current.lazy);
    std::cout << "{\"return_word\":" << result << ",\"events\":[";
    for (std::size_t i = 0; i < events.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << events[i];
    }
    std::cout << "],\"state\":" << stateJson(after, response);
    if (current.kind != "d1" && current.kind != "d2")
      std::cout << ",\"vptr_subsystem\":" << (vtable ? "true" : "false");
    std::cout << "}\n";
  }
  check(c1calls == 32 && c2calls == 32 && d1calls >= 32 && d2calls >= 32 &&
        registered == 64);
  std::cerr << "actual variant calls C1=" << c1calls << " C2=" << c2calls
            << " D1=" << d1calls << " D2=" << d2calls
            << " registered=" << registered << '\n';
}
