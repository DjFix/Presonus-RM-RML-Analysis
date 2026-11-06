#include "core/system/coredebug.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/LEDNotifyTask.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/RackPanelComponent.hpp"
#include "presonus/panel/uart_message.hpp"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
std::vector<std::string> trace;
std::vector<std::pair<char, std::string>> wireTrace;
bool observing = false;
int burnDepth = 0, clockIndex = 0;
std::int64_t ns0 = 0, ns1 = 0;
void emit(const std::string &s) {
  if (observing)
    trace.push_back(s);
}
std::string hex(const Uart_Msg_Type &m) {
  std::ostringstream s;
  s << std::hex << std::setfill('0');
  for (auto b : m.bytes)
    s << std::setw(2) << unsigned(b);
  return s.str();
}
struct Dependencies : presonus::rackpanel_port::Dependencies {
  Presonus::Panel::ControlGroup &group(int) override {
    throw std::logic_error("unused group");
  }
  Core::Portable::Component &monitorParameters() override {
    throw std::logic_error("unused monitor");
  }
  const std::vector<presonus::rackpanel_port::Channel> &
  channels() const override {
    return channels_;
  }
  int numClients() const override { return 0; }
  void removeDelegate(Presonus::Panel::RackPanelComponent &) override {}
  std::vector<presonus::rackpanel_port::Channel> channels_;
};
class MemoryPort : public Presonus::Panel::ProtocolComm {
public:
  char name;
  int mutation = 0;
  bool fail = false;
  presonus::panel_binding::PanelRegistrarPortState *state = nullptr;
  std::vector<std::string> encoded;
  Uart_Msg_Type *lastMessage = nullptr;
  explicit MemoryPort(char name) : name(name) {}
  int writeMsg(Uart_Msg_Type &m) override {
    lastMessage = &m;
    emit(std::string(1, name) + ":" + hex(m));
    if (fail)
      throw std::runtime_error("offline port failure");
    int result = ProtocolComm::writeMsg(m);
    if (mutation) {
      m.bytes[3] = 0x7e;
      if (mutation == 2)
        state->secondaryEnabled = true;
      if (mutation == 3)
        state->secondaryEnabled = false;
    }
    return result;
  }
  int write(const char *p, int n) override {
    encoded.emplace_back(p, n);
    wireTrace.emplace_back(name, std::string(p, n));
    return n;
  }
  int read(char *, int) override { return 0; }
  int open(const char *) override {
    throw std::logic_error("no device execution");
  }
  void close() override {}
  int enableHISpeed(bool) override {
    throw std::logic_error("no device execution");
  }
};
} // namespace
extern "C" void burnSymbol() asm(
    "_ZN8Presonus5Panel18RackPanelComponent20doFactoryBurnInCheckEv");
extern "C" void permissionsSymbol() asm(
    "_ZN8Presonus5Panel18RackPanelComponent23checkPermissionsPWResetEv");
extern "C" void networkSymbol() asm(
    "_ZN8Presonus5Panel18RackPanelComponent17checkNetworkResetEv");
extern "C" void
tasksSymbol() asm("_ZN8Presonus5Panel18RackPanelComponent9idleTasksEv");
extern "C" void
ledSymbol() asm("_ZN8Presonus5Panel16ControlRegistrar10setAllLedsEb");
extern "C" void
getSymbol() asm("_ZNK8Presonus5Panel14PanelRegistrar7getPortEv");
extern "C" void
baseGetSymbol() asm("_ZNK8Presonus5Panel16ControlRegistrar7getPortEv");
extern "C" void __cyg_profile_func_enter(void *fn, void *) {
  if (fn == reinterpret_cast<void *>(&burnSymbol))
    ++burnDepth;
  else if (fn == reinterpret_cast<void *>(&permissionsSymbol))
    emit("permissions");
  else if (fn == reinterpret_cast<void *>(&networkSymbol))
    emit("network");
  else if (fn == reinterpret_cast<void *>(&tasksSymbol))
    emit("tasks");
  else if (fn == reinterpret_cast<void *>(&ledSymbol))
    emit("led");
  else if (fn == reinterpret_cast<void *>(&getSymbol) ||
           fn == reinterpret_cast<void *>(&baseGetSymbol))
    emit("get");
}
extern "C" void __cyg_profile_func_exit(void *fn, void *) {
  if (fn == reinterpret_cast<void *>(&burnSymbol))
    --burnDepth;
}
extern "C" int __wrap_clock_gettime(clockid_t, timespec *t) {
  auto ns = observing && burnDepth && clockIndex++ ? ns1 : ns0;
  if (burnDepth)
    emit("clock");
  t->tv_sec = ns / 1000000000;
  t->tv_nsec = ns % 1000000000;
  return 0;
}
extern "C" void realDebug(const char *,
                          ...) asm("__real__ZN4Core11DebugPrintfEPKcz");
extern "C" void wrapDebug(const char *,
                          ...) asm("__wrap__ZN4Core11DebugPrintfEPKcz");
extern "C" void wrapDebug(const char *format, ...) {
  char text[4096];
  va_list args;
  va_start(args, format);
  std::vsnprintf(text, sizeof(text), format, args);
  va_end(args);
  if (std::string(text) == "FPR: Entering burn-in mode.\n")
    emit("debug");
  realDebug("%s", text);
}
int main(int argc, char **) {
  using namespace Presonus::Panel;
  Dependencies deps;
  MemoryPort primary('p'), secondary('s');
  presonus::panel_binding::PanelRegistrarPortState state;
  state.port = &primary;
  state.secondaryPort = &secondary;
  primary.state = &state;
  PanelRegistrar registrar(state);
  ControlRegistrar standalone;
  standalone.bindPort(&primary);
  RackPanelComponent first(deps), second(deps);
  std::uint64_t startup = 0;
  for (auto *r : {&first, &second}) {
    r->portableState().registrar = &registrar;
    r->permissionFlags = 0x18;
    r->permissionStartupMilliseconds = &startup;
  }
  if (argc > 1) {
    // Explicit adaptation failures and synchronous exception timing.
    ControlRegistrar unbound;
    bool failed = false;
    try {
      unbound.scanSurface();
    } catch (const std::logic_error &) {
      failed = true;
    }
    assert(failed);
    state.secondaryEnabled = true;
    state.secondaryPort = nullptr;
    Uart_Msg_Type m{{0x4c, 0x0f, 0x56, 0x01}};
    failed = false;
    try {
      registrar.writeDualMsg(m);
    } catch (const std::logic_error &) {
      failed = true;
    }
    assert(failed && !primary.encoded.empty());
    state.secondaryPort = &secondary;
    state.secondaryEnabled = false;
    primary.mutation = 0;
    first.burnInHeldCount = 4;
    for (int i = 1; i <= 6; ++i) {
      ns0 = ns1 = std::int64_t(i) * 501000000;
      first.doFactoryBurnInCheck();
    }
    ns0 = ns1 = 3507000000;
    primary.fail = true;
    trace.clear();
    clockIndex = 0;
    observing = true;
    failed = false;
    try {
      first.doFactoryBurnInCheck();
    } catch (const std::runtime_error &) {
      failed = true;
    }
    observing = false;
    assert(failed && clockIndex == 1 && burnDepth == 0);
    primary.fail = false;
    trace.clear();
    clockIndex = 0;
    observing = true;
    first.doFactoryBurnInCheck();
    observing = false;
    assert(clockIndex == 2);
    assert(trace.size() == 6 && trace[0] == "clock" && trace[1] == "debug" &&
           trace[2] == "led" && trace[3] == "get" && trace[4] == "p:4c0fff01" &&
           trace[5] == "clock");
    first.burnInHeldCount = 0;
    // Actual deferred removal and borrowed task lifetime through onIdle.
    struct Task : PanelTask {
      int &calls;
      explicit Task(int &c) : calls(c) {}
      bool idle() override {
        ++calls;
        return true;
      }
    };
    int calls = 0;
    Task task(calls);
    first.tasks.add(&task);
    first.tasks.add(&task);
    ns0 = 0;
    ns1 = 0;
    first.onIdle();
    assert(calls == 2 && first.tasks.count() == 0);
    // Real permissions gate runs before network, so bit 0x10 suppresses a
    // second reset. No device/network action is needed to observe this order.
    for (unsigned flags : {0u, 2u, 4u}) {
      first.permissionFlags = flags;
      ns0 = ns1 = 1001000000;
      first.onIdle();
      assert(first.permissionFlags == (flags | 0x10u));
      assert(first.tasks.count() == 0);
    }
    std::cout << "provider PASS explicit binding errors, "
                 "base-before-secondary, duplicate task removal/lifetime\n";
    return 0;
  }
  int target, enabled, heldActive, object, hasPrimary, hasSecondary,
      secondaryPresent, mutation, derived;
  std::uint32_t held;
  while (std::cin >> target >> enabled >> ns0 >> ns1 >> held >> heldActive >>
         object >> hasPrimary >> hasSecondary >> secondaryPresent >> mutation >>
         derived) {
    auto &rack = object ? second : first;
    rack.burnInHeldCount = held;
    rack.portableState().active = heldActive != 0;
    state.port = hasPrimary ? &primary : nullptr;
    state.secondaryEnabled = hasSecondary != 0;
    state.secondaryPort = secondaryPresent ? &secondary : nullptr;
    primary.mutation = mutation;
    standalone.bindPort(state.port);
    ControlRegistrar &commands =
        derived ? static_cast<ControlRegistrar &>(registrar) : standalone;
    trace.clear();
    wireTrace.clear();
    primary.lastMessage = secondary.lastMessage = nullptr;
    clockIndex = 0;
    observing = true;
    Uart_Msg_Type m{{0x4c, 0x0f, 0x56, 0x01}};
    switch (target) {
    case 0:
      rack.doFactoryBurnInCheck();
      break;
    case 1:
      rack.onIdle();
      break;
    case 2:
      commands.setAllLeds(enabled);
      break;
    case 3:
      commands.setAllMeters(enabled);
      break;
    case 4:
      commands.scanSurface();
      break;
    case 5:
      commands.ControlRegistrar::writeDualMsg(m);
      break;
    case 6:
      registrar.writeDualMsg(m);
      break;
    default:
      std::abort();
    }
    observing = false;
    if (primary.lastMessage && secondary.lastMessage)
      assert(primary.lastMessage == secondary.lastMessage);
    std::cout << "TRACE";
    for (const auto &s : trace)
      std::cout << ' ' << s;
    std::cout << '\n';
    // Every actual message uses the real ProtocolComm encoder and CCL lock.
    for (const auto &[name, text] : wireTrace) {
      std::cout << "WIRE " << name << ' ';
      for (unsigned char c : text)
        std::cout << std::hex << std::setw(2) << std::setfill('0')
                  << unsigned(c);
      std::cout << std::dec << '\n';
    }
    primary.encoded.clear();
    secondary.encoded.clear();
  }
}
