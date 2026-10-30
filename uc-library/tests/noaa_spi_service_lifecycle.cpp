#include "presonus/noaa/spi_packets.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <new>
#include <sstream>
#include <string>
#include <vector>

using presonus::noaa::SpiServiceAccess;
using Presonus::NOAA::TCardSPI;
using Presonus::Panel::InputPin;
using Presonus::Panel::PinStateObserver;
using presonus::surface_panel_port::InputPinAccess;
using presonus::surface_panel_port::InputPinIO;
static void checked(bool v, const char *expression, int line) {
  if (!v) {
    std::fprintf(stderr, "Lifecycle assertion line%d: %s\n", line, expression);
    std::abort();
  }
}
#define require(v) checked((v), #v, __LINE__)
static std::string hex(const std::string &s) {
  const char *digits = "0123456789abcdef";
  std::string out;
  for (unsigned char c : s) {
    out += digits[c >> 4];
    out += digits[c & 15];
  }
  return out;
}
extern "C" std::size_t spiDerivedSize();
extern "C" TCardSPI *spiDerivedRootAddress(void *);
extern "C" TCardSPI *spiConstructDerived(void *);
extern "C" void spiDestroyDerived(TCardSPI *);
extern "C" void spiCtorEntry(TCardSPI *) asm("_ZN8Presonus4NOAA8TCardSPIC1Ev");
extern "C" void spiNativeD1(TCardSPI *);
extern "C" void spiNativeD0(TCardSPI *);
struct Capture {
  TCardSPI *root = nullptr, *initialSingleton = nullptr,
           *finalSingleton = nullptr;
  std::array<InputPin *, 2> pins{};
  unsigned allocated = 0;
  std::uintptr_t ctorStart = 0, ctorSize = 0;
  bool constructing = false, quiet = false;
  int depth = 0, fdAtUnlock = -1;
  std::string trace;
  void event(const char *kind, const std::vector<std::string> &args) {
    if (quiet)
      return;
    trace += kind;
    trace += '|';
    for (unsigned i = 0; i < args.size(); ++i) {
      if (i)
        trace += ',';
      trace += args[i];
    }
    trace += ';';
  }
};
static Capture *capture = nullptr;
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" __attribute__((noinline)) void *__wrap__Znwm(std::size_t size) {
  void *pointer = __real__Znwm(size);
  const auto caller =
      reinterpret_cast<std::uintptr_t>(__builtin_return_address(0));
  if (capture && capture->constructing && size == sizeof(InputPin) &&
      caller >= capture->ctorStart &&
      caller < capture->ctorStart + capture->ctorSize) {
    require(capture->allocated < 2);
    capture->pins[capture->allocated++] = static_cast<InputPin *>(pointer);
    capture->event("N", {std::to_string(capture->allocated)});
  }
  return pointer;
}
static void deleting(void *pointer) {
  if (!capture)
    return;
  if (pointer == capture->root) {
    require(SpiServiceAccess::singleton() == capture->finalSingleton);
    capture->event("X", {"R"});
    return;
  }
  for (unsigned i = 0; i < 2; ++i)
    if (pointer == capture->pins[i]) {
      require(SpiServiceAccess::singleton() == capture->initialSingleton);
      capture->event("X", {std::to_string(i + 1)});
      return;
    }
}
extern "C" void __wrap__ZdlPv(void *p) {
  deleting(p);
  __real__ZdlPv(p);
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) {
  deleting(p);
  __real__ZdlPvm(p, n);
}
extern "C" void
__real__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *);
extern "C" void
__real__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *);
extern "C" void
__wrap__ZN4Core8Platform9PosixLock4lockEv(Core::Platform::PosixLock *lock) {
  __real__ZN4Core8Platform9PosixLock4lockEv(lock);
  if (capture && !capture->quiet) {
    require(static_cast<void *>(lock) ==
            static_cast<void *>(&SpiServiceAccess::state(*capture->root).lock));
    capture->event("K+", {std::to_string(++capture->depth)});
  }
}
extern "C" void
__wrap__ZN4Core8Platform9PosixLock6unlockEv(Core::Platform::PosixLock *lock) {
  if (capture && !capture->quiet) {
    require(static_cast<void *>(lock) ==
                static_cast<void *>(
                    &SpiServiceAccess::state(*capture->root).lock) &&
            capture->depth > 0);
    capture->fdAtUnlock = SpiServiceAccess::descriptor(*capture->root);
    capture->event("K-", {std::to_string(capture->depth--)});
  }
  __real__ZN4Core8Platform9PosixLock6unlockEv(lock);
}
struct Pins final : InputPinIO {
  Capture &record;
  unsigned fail = 0, opens = 0;
  bool errors = false;
  std::array<unsigned, 7> owner{};
  explicit Pins(Capture &r) : record(r) {}
  static std::FILE *file(unsigned i) {
    return i ? reinterpret_cast<std::FILE *>(std::uintptr_t(0x8000 + i * 256))
             : nullptr;
  }
  static unsigned id(std::FILE *p) {
    if (!p)
      return 0;
    for (unsigned i = 1; i <= 6; ++i)
      if (p == file(i))
        return i;
    std::abort();
  }
  std::array<std::uint32_t, 5> state(unsigned identity) const {
    require(identity >= 1 && identity <= 2);
    auto *p = record.pins[identity - 1];
    auto *observer = InputPinAccess::observer(*p);
    require(observer == nullptr ||
            observer == static_cast<PinStateObserver *>(record.root));
    return {static_cast<std::uint32_t>(InputPinAccess::number(*p)),
            static_cast<std::uint32_t>(InputPinAccess::state(*p)),
            static_cast<std::uint32_t>(InputPinAccess::last(*p)),
            id(InputPinAccess::file(*p)), observer != nullptr};
  }
  void event(const char *kind, std::vector<std::string> args,
             unsigned identity) {
    if (record.quiet)
      return;
    require(SpiServiceAccess::singleton() == record.initialSingleton);
    for (auto v : state(identity))
      args.push_back(std::to_string(v));
    record.event(kind, args);
  }
  std::FILE *open(const char *path, const char *mode) override {
    event("O", {hex(path), hex(mode)}, record.allocated);
    ++opens;
    if (opens == fail)
      return nullptr;
    require(opens <= 6);
    owner[opens] = record.allocated;
    return file(opens);
  }
  int printPin(std::FILE *p, const char *format, int pin) override {
    require(std::string(format) == "%d");
    event("F",
          {std::to_string(id(p)),
           std::to_string(static_cast<std::uint32_t>(pin))},
          owner[id(p)]);
    return errors ? -1 : 1;
  }
  int close(std::FILE *p) override {
    event("Z", {std::to_string(id(p))}, owner[id(p)]);
    return errors ? -1 : 0;
  }
  void formatPath(char *out, std::size_t n, const char *format,
                  int pin) override {
    event("S", {hex(format), std::to_string(static_cast<std::uint32_t>(pin))},
          record.allocated);
    std::snprintf(out, n, format, pin);
  }
  std::size_t write(const void *data, std::size_t n, std::size_t count,
                    std::FILE *p) override {
    require(n == 1 && count == 2 &&
            std::string(static_cast<const char *>(data), 2) == "in");
    event("W", {std::to_string(id(p))}, owner[id(p)]);
    return errors ? 0 : 2;
  }
  int buffering(std::FILE *p, char *buffer, int mode, std::size_t n) override {
    require(buffer == nullptr && mode == 2 && n == 0);
    event("B", {std::to_string(id(p))}, owner[id(p)]);
    return errors ? -1 : 0;
  }
  void rewind(std::FILE *) override { std::abort(); }
  int flush(std::FILE *) override { std::abort(); }
  int get(std::FILE *) override { std::abort(); }
  void notify(PinStateObserver *, int, int) override { std::abort(); }
  void log(const char *s) override { event("L", {hex(s)}, record.allocated); }
};
struct SPI final : presonus::noaa::SpiServiceIO {
  Capture &record;
  bool errors = false;
  explicit SPI(Capture &r) : record(r) {}
  int open(const char *, int) override { std::abort(); }
  int maxSpeed(int, std::uint32_t) override { std::abort(); }
  int transfer(int, const presonus::noaa::SpiTransfer &) override {
    std::abort();
  }
  int close(int fd) override {
    require(record.depth == 1 &&
            SpiServiceAccess::singleton() == record.initialSingleton);
    record.event("C", {std::to_string(fd)});
    return errors ? -1 : 0;
  }
  int errorNumber() override { std::abort(); }
  std::int64_t rawTicks() override { std::abort(); }
  void diagnostic(bool, const char *, int, bool) override { std::abort(); }
};
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const auto ctorSize = std::stoull(argv[2]);
  require(ctorSize > 0);
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0, d0 = 0, d1 = 0, d2 = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    unsigned index, fail, errors, singleton, files[2], expectedSingleton;
    int fd, expectedFd;
    std::string mode, expectedTrace;
    std::array<std::array<std::uint32_t, 5>, 2> expectedPins{};
    row >> index >> mode >> fail >> errors >> singleton >> fd >> files[0] >>
        files[1] >> expectedFd >> expectedSingleton;
    for (auto &p : expectedPins)
      for (auto &v : p)
        row >> v;
    row >> expectedTrace;
    require(bool(row));
    Capture record;
    record.trace.reserve(16384);
    Pins pins(record);
    SPI io(record);
    pins.errors = io.errors = errors != 0;
    const unsigned variant = mode == "C1"   ? 0
                             : mode == "C2" ? 1
                             : mode == "D1" ? 2
                             : mode == "D2" ? 3
                             : mode == "D0" ? 4
                                            : 5;
    require(variant < 5);
    const bool derived = variant == 1 || variant == 3;
    void *storage =
        ::operator new(derived ? spiDerivedSize() : sizeof(TCardSPI));
    record.root = derived ? spiDerivedRootAddress(storage)
                          : static_cast<TCardSPI *>(storage);
    auto *other = reinterpret_cast<TCardSPI *>(
        reinterpret_cast<std::uintptr_t>(record.root) + 0x10000);
    record.initialSingleton = singleton == 1   ? record.root
                              : singleton == 2 ? other
                                               : nullptr;
    record.finalSingleton = singleton == 1 ? nullptr : record.initialSingleton;
    SpiServiceAccess::singleton(record.initialSingleton);
    record.ctorStart = reinterpret_cast<std::uintptr_t>(&spiCtorEntry);
    record.ctorSize = ctorSize;
    record.constructing = true;
    auto *previousPins =
        presonus::surface_panel_port::setInputPinConstructionIO(&pins);
    auto *previousSPI = presonus::noaa::setSpiServiceConstructionIO(&io);
    const bool constructor = variant < 2;
    record.quiet = !constructor;
    pins.fail = constructor ? fail : 0;
    capture = &record;
    if (derived)
      require(spiConstructDerived(storage) == record.root);
    else
      new (storage) TCardSPI;
    record.constructing = false;
    require(record.allocated == 2 &&
            SpiServiceAccess::pinCount(*record.root) == 2);
    for (unsigned i = 0; i < 2; ++i)
      require(SpiServiceAccess::pin(*record.root, i) == record.pins[i]);
    require(SpiServiceAccess::state(*record.root).count == 0 &&
            SpiServiceAccess::state(*record.root).disabled == 0 &&
            SpiServiceAccess::state(*record.root).receivers.count() == 0 &&
            SpiServiceAccess::state(*record.root).receivers.getCapacity() == 0);
    std::array<std::array<std::uint32_t, 5>, 2> snapshots{};
    if (constructor) {
      for (unsigned i = 0; i < 2; ++i)
        snapshots[i] = pins.state(i + 1);
      require(SpiServiceAccess::descriptor(*record.root) == expectedFd &&
              SpiServiceAccess::singleton() == record.initialSingleton);
    } else {
      std::array<InputPin *, 32> list{};
      list[0] = record.pins[0];
      list[1] = record.pins[1];
      SpiServiceAccess::bind(*record.root, io, fd, list, 2);
      for (unsigned i = 0; i < 2; ++i) {
        InputPinAccess::bind(*record.pins[i], pins, i ? 137 : 34, 0, 0,
                             Pins::file(files[i]),
                             static_cast<PinStateObserver *>(record.root));
        if (files[i])
          pins.owner[files[i]] = i + 1;
        snapshots[i] = pins.state(i + 1);
      }
      record.trace.clear();
      record.quiet = false;
      if (variant == 4) {
        spiNativeD0(record.root);
        ++d0;
      } else if (variant == 2) {
        spiNativeD1(record.root);
        ++d1;
      } else {
        spiDestroyDerived(record.root);
        ++d2;
      }
      require(record.fdAtUnlock == expectedFd);
    }
    require(record.depth == 0);
    auto *expectedPointer = expectedSingleton == 1   ? record.root
                            : expectedSingleton == 2 ? other
                                                     : nullptr;
    const bool okay = snapshots == expectedPins &&
                      hex(record.trace) == expectedTrace &&
                      SpiServiceAccess::singleton() == expectedPointer;
    if (!okay) {
      std::fprintf(stderr, "Lifecycle mismatch %u mode%s trace%s expected%s\n",
                   index, mode.c_str(), hex(record.trace).c_str(),
                   expectedTrace.c_str());
      return 1;
    }
    if (constructor) {
      record.quiet = true;
      if (derived)
        spiDestroyDerived(record.root);
      else
        spiNativeD1(record.root);
    }
    capture = nullptr;
    if (variant != 4)
      ::operator delete(storage);
    presonus::surface_panel_port::setInputPinConstructionIO(previousPins);
    presonus::noaa::setSpiServiceConstructionIO(previousSPI);
    SpiServiceAccess::singleton(nullptr);
    ++cases;
  }
  if (!(input.eof() && cases > 0 && d0 && d1 && d2))
    std::fprintf(
        stderr,
        "Final input=%s open%d eof%d fail%d bad%d cases%u D0%u D1%u D2%u\n",
        argv[1], input.is_open(), input.eof(), input.fail(), input.bad(), cases,
        d0, d1, d2);
  require(input.eof() && cases > 0 && d0 && d1 && d2);
  std::printf("PASS: %u original ARM owning SPI lifecycle cases; real vtable "
              "D1=%u D0=%u, derived base D2=%u, real pin/self deallocation\n",
              cases, d1, d0, d2);
}
