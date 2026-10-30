#include "core/system/corethread.h"
#include "dice_fixture_receivers.hpp"
#include "presonus/dice/manager.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Presonus::DICE::Dice3Manager;
using Presonus::DICE::Dice3Subsystem;
using Presonus::DICE::Dice3Uart;
void require(bool value, const char *message) {
  if (!value)
    throw std::runtime_error(message);
}
std::int32_t integer(std::uint32_t word) {
  std::int32_t value;
  std::memcpy(&value, &word, sizeof value);
  return value;
}
struct Case {
  unsigned kind, stop, stopAfter, updateAfter;
  std::uint32_t arg, returnWord;
  std::vector<std::int64_t> ticks;
  std::array<std::uint32_t, 5> words, updated;
};
struct Event {
  const char *kind;
  std::int64_t value;
  bool argument = true;
};
struct Context {
  Case input;
  Dice3Manager *manager;
  Dice3Subsystem *subsystem;
  Dice3Uart *uart;
  std::vector<Event> events;
  unsigned sleeps = 0, clocks = 0;
};
Context *current = nullptr;
void store(Dice3Subsystem &subsystem,
           const std::array<std::uint32_t, 5> &words) {
  auto &state = subsystem.portableState();
  state.infoWords = {words[0], words[1], words[2]};
  state.rateWord = words[3];
  state.clockWord = words[4];
}
class Routes final : public presonus::dice::RouteSink {
  std::int32_t setRoute(const presonus::dice::RouteTuple &) override {
    throw std::runtime_error("Unexpected routing boundary in manager fixture");
  }
};
class Callbacks final : public presonus::dice::AssemblyCallbacks {
  void noReceiver(unsigned) override {
    throw std::runtime_error("Unexpected UART callback");
  }
  void packetLog(const Presonus::DICE::SysexPacket &) override {
    throw std::runtime_error("Unexpected UART log");
  }
  void sourcePortError(presonus::dice::AssemblyError, unsigned) override {
    throw std::runtime_error("Unexpected UART error");
  }
};
class Services final : public presonus::dice::ManagerServices {
public:
  explicit Services(Context &context) : c(context) {}
  std::int64_t clockRawTicks() override {
    require(c.clocks < c.input.ticks.size(), "Native clock stream exhausted");
    const auto value = c.input.ticks[c.clocks++];
    c.events.push_back({"clock", value});
    return value;
  }
  void sleepMilliseconds(std::uint32_t milliseconds) override {
    c.events.push_back({"sleep", milliseconds});
    ++c.sleeps;
    if (c.input.kind == 3) {
      require(milliseconds == 1, "Thread sleep duration");
      if (c.sleeps == c.input.stopAfter)
        c.manager->setPortableStopByte(1);
    } else {
      require(c.input.kind == 4 && milliseconds == 100,
              "Information sleep duration");
      if (c.sleeps == c.input.updateAfter)
        store(*c.subsystem, c.input.updated);
    }
  }
  void terminateThread() override {
    c.events.push_back({"terminate", c.manager->portableStopByte()});
  }

private:
  Context &c;
};
class Worker final : public Core::Threads::Thread {
public:
  std::atomic<bool> started{false}, unwound{false};
  int threadEntry() override {
    struct Guard {
      std::atomic<bool> &flag;
      ~Guard() { flag.store(true); }
    } guard{unwound};
    started.store(true);
    for (;;)
      Core::Threads::CurrentThread::sleep(1);
  }
};
int providerSmoke() {
  Worker worker;
  presonus::dice::CclManagerServices services(worker);
  const auto before = services.clockRawTicks();
  services.sleepMilliseconds(1);
  require(services.clockRawTicks() >= before,
          "Actual source-backed Core clock");
  worker.start();
  for (unsigned i = 0; !worker.started.load() && i < 1000; ++i)
    Core::Threads::CurrentThread::sleep(1);
  require(worker.started.load(), "Actual CCL worker did not start");
  services.terminateThread();
  require(worker.join(1000), "Actual CCL worker join");
  require(worker.unwound.load(), "Actual canceled worker stack did not unwind");
  std::cout << "PASS actual CCL clock/sleep/thread terminate/join/unwind\n";
  return 0;
}
} // namespace

extern "C" std::int32_t
__wrap__ZN8Presonus4DICE14Dice3Subsystem7setRateENS0_15Dice3SampleRateE(
    Dice3Subsystem *self, Presonus::DICE::Dice3SampleRate rate) {
  require(current && self == current->subsystem, "Rate target identity");
  current->events.push_back({"rate", static_cast<std::uint32_t>(rate)});
  return integer(current->input.returnWord);
}
extern "C" std::int32_t
__wrap__ZN8Presonus4DICE14Dice3Subsystem14setClockSourceENS0_16Dice3ClockSourceE(
    Dice3Subsystem *self, Presonus::DICE::Dice3ClockSource source) {
  require(current && self == current->subsystem, "Clock target identity");
  current->events.push_back({"profile", static_cast<std::uint32_t>(source)});
  return integer(current->input.returnWord);
}
extern "C" void __wrap__ZN8Presonus4DICE9Dice3Uart6onIdleEv(Dice3Uart *self) {
  require(current && self == current->uart, "UART idle target identity");
  current->events.push_back({"idle", 0, false});
}

int main(int argc, char **argv) {
  try {
    if (argc == 2 && std::string(argv[1]) == "--provider-smoke")
      return providerSmoke();
    presonus::dice::UartAssemblyState uartState(std::array<unsigned char, 67>{},
                                                0, 0);
    Callbacks callbacks;
    Dice3Uart uart(uartState, callbacks);
    Routes routes;
    Case input{};
    unsigned tickCount;
    while (std::cin >> input.kind >> input.arg >> input.returnWord >>
           input.stop >> input.stopAfter >> input.updateAfter >> tickCount) {
      input.ticks.resize(tickCount);
      for (auto &value : input.ticks)
        std::cin >> value;
      for (auto &word : input.words)
        std::cin >> word;
      for (auto &word : input.updated)
        std::cin >> word;
      require(bool(std::cin), "Incomplete fixture input");
      Dice3Manager manager(routes);
      Dice3Subsystem subsystem(presonus::dice::BorrowedSubsystemSetup{});
      store(subsystem, input.words);
      Context context{input, &manager, &subsystem, &uart};
      Services services(context);
      manager.setPortableRuntime(subsystem, uart, services);
      manager.setPortableStopByte(static_cast<unsigned char>(input.stop));
      current = &context;
      std::uint32_t result = 0;
      Presonus::DICE::DiceInfo info;
      switch (input.kind) {
      case 0:
        result = manager.setDiceClockRate(
            static_cast<Presonus::DICE::Dice3SampleRate>(integer(input.arg)));
        break;
      case 1:
        result = manager.setDiceClockProfile(
            static_cast<Presonus::DICE::Dice3ClockProfile>(integer(input.arg)));
        break;
      case 2:
        manager.release();
        break;
      case 3:
        result = manager.threadEntry();
        break;
      case 4:
        result = manager.getDice3Info(&info);
        break;
      default:
        throw std::runtime_error("Unknown fixture method");
      }
      std::cout << "{\"events\":[";
      for (std::size_t i = 0; i < context.events.size(); ++i) {
        if (i)
          std::cout << ',';
        const auto &event = context.events[i];
        std::cout << "[\"" << event.kind << '\"';
        if (event.argument)
          std::cout << ',' << event.value;
        std::cout << ']';
      }
      std::cout << "],\"stop\":" << unsigned(manager.portableStopByte());
      if (input.kind != 2)
        std::cout << ",\"return_word\":" << result;
      if (input.kind == 4) {
        std::cout << ",\"words\":[";
        for (std::size_t i = 0; i < info.portableWords.size(); ++i) {
          if (i)
            std::cout << ',';
          std::cout << info.portableWords[i];
        }
        std::cout << ']';
      }
      std::cout << "}\n";
      current = nullptr;
    }
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
