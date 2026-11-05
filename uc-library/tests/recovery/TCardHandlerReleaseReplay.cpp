#include "presonus/noaa/card.hpp"
#include "presonus/noaa/card_handler.hpp"
#include "presonus/noaa/spi_packets.hpp"
#include <atomic>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <pthread.h>
#include <string>
#include <thread>

namespace {
void require(bool ok) {
  if (!ok)
    std::abort();
}
struct Response final : presonus::dice::ResponseServices {
  std::int64_t clockRawTicks() override { std::abort(); }
  void pumpIdle(bool) override { std::abort(); }
  void sleepMilliseconds(std::uint32_t) override { std::abort(); }
  void timeoutNotice(bool, std::uint32_t, std::uint32_t) override {
    std::abort();
  }
};
struct IO final : presonus::noaa::SpiServiceIO {
  int calls = 0;
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const presonus::noaa::SpiTransfer &) override {
    std::abort();
  }
  int close(int) override { std::abort(); }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
struct GPIO final : presonus::surface_panel_port::InputPinIO {
  unsigned opens = 0, closes = 0;
  std::FILE *open(const char *, const char *) override {
    ++opens;
    return reinterpret_cast<std::FILE *>(std::uintptr_t(0x1000 + opens));
  }
  int printPin(std::FILE *, const char *, int pin) override {
    require(pin == 34 || pin == 137);
    return 1;
  }
  int close(std::FILE *) override {
    ++closes;
    return 0;
  }
  void formatPath(char *out, std::size_t n, const char *format,
                  int pin) override {
    std::snprintf(out, n, format, pin);
  }
  std::size_t write(const void *, std::size_t size, std::size_t count,
                    std::FILE *) override {
    return size * count;
  }
  int buffering(std::FILE *, char *, int, std::size_t) override { return 0; }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
  void log(const char *) override { std::abort(); }
};
struct Card final : Presonus::NOAA::TCard {
  Card(presonus::noaa::CardState &s, Response &r, IO &i)
      : TCard(presonus::noaa::cardSetupTag, s, r, i) {}
  bool updateFirmware(Presonus::UC::IFirmwareUpdateListener *, int) override {
    std::abort();
  }
};
presonus::noaa::CardHandlerState *capturedState = nullptr;
std::string trace;
std::atomic<bool> entered{false}, consumed{false}, cleaned{false},
    cancellationIssued{false};
struct Handler final : Presonus::NOAA::TCardHandler {
  presonus::noaa::CardHandlerState &state;
  Handler(presonus::noaa::CardHandlerState &s, Response &r)
      : TCardHandler(presonus::noaa::cardHandlerSetupTag, s, r), state(s) {}
  void setProperty(const Core::Property &) override { std::abort(); }
  int threadEntry() override {
    // Make cancellation pending until natural bounded exit, so acquire-load
    // consumption and cleanup are observed reliably after the real cancel.
    require(pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, nullptr) == 0);
    struct Cleanup {
      ~Cleanup() { cleaned.store(true); }
    } cleanup;
    entered.store(true, std::memory_order_release);
    const auto until =
        std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (!state.stopRequested.load(std::memory_order_acquire)) {
      require(std::chrono::steady_clock::now() < until);
      std::this_thread::yield();
    }
    auto *spi = presonus::noaa::SpiServiceAccess::singleton();
    require(spi && presonus::noaa::SpiServiceAccess::state(*spi).disabled == 1);
    consumed.store(true);
    // Stay alive through the actual provider cancellation call. Cancellation
    // remains disabled, preserving defined C++ cleanup at natural exit.
    while (!cancellationIssued.load(std::memory_order_acquire)) {
      require(std::chrono::steady_clock::now() < until);
      std::this_thread::yield();
    }
    return 0;
  }
};
GPIO *exitGPIO;
void verifyCleanup() {
  require(exitGPIO->opens == 6 && exitGPIO->closes == 6);
  require(presonus::noaa::SpiServiceAccess::singleton() == nullptr);
  std::cout << "PASS singleton GPIO cleanup through captured I/O\n";
}
} // namespace

extern "C" void
__real__ZN8Presonus4NOAA8TCardSPI7releaseEv(Presonus::NOAA::TCardSPI *);
extern "C" void
__wrap__ZN8Presonus4NOAA8TCardSPI7releaseEv(Presonus::NOAA::TCardSPI *spi) {
  require(capturedState && !capturedState->stopRequested.load());
  trace += "spi.release;";
  __real__ZN8Presonus4NOAA8TCardSPI7releaseEv(spi);
  require(presonus::noaa::SpiServiceAccess::state(*spi).disabled == 1);
}
extern "C" void __real__ZN4Core8Platform11PosixThread9terminateEv(
    Core::Platform::PosixThread *);
extern "C" void __wrap__ZN4Core8Platform11PosixThread9terminateEv(
    Core::Platform::PosixThread *thread) {
  require(entered.load(std::memory_order_acquire));
  require(capturedState &&
          capturedState->stopRequested.load(std::memory_order_acquire));
  auto *spi = presonus::noaa::SpiServiceAccess::singleton();
  require(spi && presonus::noaa::SpiServiceAccess::state(*spi).disabled == 1);
  trace += "stop=1;terminate;";
  __real__ZN4Core8Platform11PosixThread9terminateEv(thread);
  cancellationIssued.store(true, std::memory_order_release);
}
int main(int argc, char **argv) {
  require(argc == 4);
  const bool present = std::string(argv[1]) == "present";
  const unsigned seed = std::stoul(argv[2]);
  std::ifstream fixture(argv[3]);
  std::string expected;
  std::getline(fixture, expected);
  require(fixture.good() && expected == "spi.release;stop=1;terminate;");
  static IO io;
  static GPIO gpio;
  exitGPIO = &gpio;
  // Registered before actual singleton construction, so it observes
  // destruction.
  require(std::atexit(verifyCleanup) == 0);
  presonus::noaa::setSpiServiceConstructionIO(&io);
  presonus::surface_panel_port::setInputPinConstructionIO(&gpio);
  require(presonus::noaa::SpiServiceAccess::singleton() == nullptr);
  if (present) {
    auto &spi = Presonus::NOAA::TCardSPI::instance();
    presonus::noaa::SpiServiceAccess::state(spi).disabled = seed;
    require(gpio.opens == 6 && gpio.closes == 4);
  }
  Response response;
  presonus::noaa::CardState cardState{};
  Card card(cardState, response, io);
  presonus::noaa::CardHandlerState state{card};
  capturedState = &state;
  Handler handler(state, response);
  handler.start();
  const auto until = std::chrono::steady_clock::now() + std::chrono::seconds(3);
  while (!entered.load(std::memory_order_acquire)) {
    require(std::chrono::steady_clock::now() < until);
    std::this_thread::yield();
  }
  Core::IPropertyHandler &interface = handler;
  interface.release();
  require(handler.join(3000));
  require(trace == expected && consumed.load() && cleaned.load());
  require(gpio.opens == 6 && gpio.closes == 4);
  auto *spi = presonus::noaa::SpiServiceAccess::singleton();
  require(spi && presonus::noaa::SpiServiceAccess::descriptor(*spi) == -1);
  std::cout << "PASS " << argv[1] << " seed=" << seed << " " << trace
            << " live CCL thread joined; stop consumed; cleanup observed\n";
}
