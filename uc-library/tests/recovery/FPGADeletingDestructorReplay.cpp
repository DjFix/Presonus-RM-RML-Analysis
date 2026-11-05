#include "presonus/noaa/TCardFPGAUpdater.hpp"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <new>

using presonus::noaa::SpiServiceAccess;
using Presonus::NOAA::TCardFPGAUpdater;
using Presonus::NOAA::TCardSPI;
namespace {
void *watched = nullptr;
unsigned releases = 0;
unsigned unregisterBeforeRelease = 0;
TCardSPI *registry = nullptr;
void release(void *p) {
  if (p && p == watched) {
    ++releases;
    assert(releases == 1);
    assert(registry);
    assert(SpiServiceAccess::state(*registry).receivers.index(
               static_cast<Presonus::NOAA::ISysexReceiver *>(
                   static_cast<TCardFPGAUpdater *>(p))) == -1);
    ++unregisterBeforeRelease;
  }
  std::free(p);
}
struct SPI final : presonus::noaa::SpiServiceIO {
  int calls = 0;
  int open(const char *, int) override {
    ++calls;
    return -1;
  }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const presonus::noaa::SpiTransfer &) override {
    std::abort();
  }
  int close(int) override { std::abort(); }
  int errorNumber() override { return 0; }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override {}
};
struct GPIO final : presonus::surface_panel_port::InputPinIO {
  int opens = 0;
  std::FILE *open(const char *, const char *) override {
    ++opens;
    return nullptr;
  }
  int printPin(std::FILE *, const char *, int) override { std::abort(); }
  int close(std::FILE *) override { std::abort(); }
  void formatPath(char *, std::size_t, const char *, int) override {
    std::abort();
  }
  std::size_t write(const void *, std::size_t, std::size_t,
                    std::FILE *) override {
    std::abort();
  }
  int buffering(std::FILE *, char *, int, std::size_t) override {
    std::abort();
  }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(Presonus::Panel::PinStateObserver *, int, int) override {
    std::abort();
  }
  void log(const char *) override {}
};
} // namespace
// Interception forwards to real libc deallocation, and verifies registry
// removal at the actual emitted D0 deallocation call, rather than inventing an
// event.
void operator delete(void *p) noexcept { release(p); }
void operator delete(void *p, std::size_t) noexcept { release(p); }
extern "C" void
d0(TCardFPGAUpdater *) asm("_ZN8Presonus4NOAA16TCardFPGAUpdaterD0Ev");
extern "C" void
d1(TCardFPGAUpdater *) asm("_ZN8Presonus4NOAA16TCardFPGAUpdaterD1Ev");
extern "C" void
d2(TCardFPGAUpdater *) asm("_ZN8Presonus4NOAA16TCardFPGAUpdaterD2Ev");
int main() {
  static SPI spi;
  static GPIO gpio;
  auto *oldSpi = presonus::noaa::setSpiServiceConstructionIO(&spi);
  auto *oldGpio =
      presonus::surface_panel_port::setInputPinConstructionIO(&gpio);
  assert(!SpiServiceAccess::singleton());
  // Lazy singleton construction is covered under both captures, before any
  // updater constructor or destructor can access the singleton.
  auto *updater = new TCardFPGAUpdater(nullptr, nullptr);
  registry = SpiServiceAccess::singleton();
  assert(registry && gpio.opens == 2 && spi.calls == 0);
  auto &receivers = SpiServiceAccess::state(*registry).receivers;
  assert(receivers.count() == 1 && receivers.at(0) == updater);
  watched = updater;
  d0(updater);
  assert(releases == 1 && unregisterBeforeRelease == 1 &&
         receivers.count() == 0);
  watched = nullptr;
  // Existing singleton and unrelated registered receiver remain intact.
  auto *keep = new TCardFPGAUpdater(nullptr, nullptr);
  updater = new TCardFPGAUpdater(nullptr, nullptr);
  assert(receivers.count() == 2);
  watched = updater;
  releases = 0;
  unregisterBeforeRelease = 0;
  d0(updater);
  assert(releases == 1 && unregisterBeforeRelease == 1 &&
         receivers.count() == 1);
  assert(receivers.at(0) == keep);
  watched = nullptr;
  delete keep;
  // D1 and D2 execute on placement storage; no deallocation is allowed.
  for (auto destructor : {d1, d2}) {
    alignas(TCardFPGAUpdater) unsigned char storage[sizeof(TCardFPGAUpdater)];
    updater = new (storage) TCardFPGAUpdater(nullptr, nullptr);
    watched = updater;
    releases = 0;
    destructor(updater);
    assert(releases == 0 && receivers.count() == 0);
    watched = nullptr;
  }
  assert(gpio.opens == 2 && spi.calls == 0);
  // CCL owns the lazy singleton through DeletableList. Static captures were
  // initialized first, so they outlive its actual shutdown destruction.
  registry = nullptr;
  presonus::surface_panel_port::setInputPinConstructionIO(oldGpio);
  presonus::noaa::setSpiServiceConstructionIO(oldSpi);
  std::puts("D0 lazy/existing: actual unregister then real free exactly once; "
            "D1/D2: unregister without free; hardware calls captured");
}
