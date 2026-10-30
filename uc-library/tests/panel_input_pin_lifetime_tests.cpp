#include "presonus/surface_panel/InputPin.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <new>
#include <sstream>
#include <string>
#include <vector>

using Presonus::Panel::InputPin;
using Presonus::Panel::PinStateObserver;
using presonus::surface_panel_port::InputPinAccess;
using presonus::surface_panel_port::InputPinIO;
static std::string hex(const std::string &value) {
  const char *digits = "0123456789abcdef";
  std::string result;
  for (unsigned char byte : value) {
    result += digits[byte >> 4];
    result += digits[byte & 15];
  }
  return result;
}
static std::string word(std::uint32_t value) { return std::to_string(value); }
struct FakeIO final : InputPinIO {
  InputPin *pin = nullptr;
  bool frozen = false, quiet = false;
  std::array<std::uint32_t, 5> snapshot{};
  unsigned failOpen = 0, openCount = 0;
  bool errors = false;
  std::vector<int> samples;
  std::size_t nextSample = 0;
  std::string trace;
  static std::FILE *file(unsigned id) {
    return id ? reinterpret_cast<std::FILE *>(
                    std::uintptr_t(0x4000 + id * 0x100))
              : nullptr;
  }
  static unsigned fileId(std::FILE *value) {
    return value
               ? static_cast<unsigned>(
                     (reinterpret_cast<std::uintptr_t>(value) - 0x4000) / 0x100)
               : 0;
  }
  static PinStateObserver *observer(unsigned id) {
    return id ? reinterpret_cast<PinStateObserver *>(
                    std::uintptr_t(0x8000 + id * 0x100))
              : nullptr;
  }
  static unsigned observerId(PinStateObserver *value) {
    return value
               ? static_cast<unsigned>(
                     (reinterpret_cast<std::uintptr_t>(value) - 0x8000) / 0x100)
               : 0;
  }
  std::array<std::uint32_t, 5> state() const {
    if (frozen)
      return snapshot;
    return {static_cast<std::uint32_t>(InputPinAccess::number(*pin)),
            static_cast<std::uint32_t>(InputPinAccess::state(*pin)),
            static_cast<std::uint32_t>(InputPinAccess::last(*pin)),
            fileId(InputPinAccess::file(*pin)),
            observerId(InputPinAccess::observer(*pin))};
  }
  void event(char kind, const std::vector<std::string> &args) {
    if (quiet)
      return;
    trace += kind;
    trace += '|';
    for (unsigned i = 0; i < args.size(); ++i) {
      if (i)
        trace += ',';
      trace += args[i];
    }
    trace += '|';
    const auto values = state();
    for (unsigned i = 0; i < values.size(); ++i) {
      if (i)
        trace += ',';
      trace += word(values[i]);
    }
    trace += '\n';
  }
  std::FILE *open(const char *path, const char *mode) override {
    event('O', {hex(path), hex(mode)});
    ++openCount;
    return openCount == failOpen ? nullptr : file(openCount);
  }
  int printPin(std::FILE *stream, const char *format, int number) override {
    event('F', {word(fileId(stream)), hex(format),
                word(static_cast<std::uint32_t>(number))});
    return errors ? -1 : 1;
  }
  int close(std::FILE *stream) override {
    event('C', {word(fileId(stream))});
    return errors ? -1 : 0;
  }
  void formatPath(char *output, std::size_t capacity, const char *format,
                  int number) override {
    event('S', {hex(format), word(static_cast<std::uint32_t>(number))});
    std::snprintf(output, capacity, format, number);
  }
  std::size_t write(const void *data, std::size_t size, std::size_t count,
                    std::FILE *stream) override {
    event('W', {word(fileId(stream)),
                hex(std::string(static_cast<const char *>(data), size * count)),
                word(size), word(count)});
    return errors ? 0 : count;
  }
  int buffering(std::FILE *stream, char *buffer, int mode,
                std::size_t size) override {
    event('B', {word(fileId(stream)), word(buffer == nullptr), word(mode),
                word(size)});
    return errors ? -1 : 0;
  }
  void rewind(std::FILE *stream) override {
    event('A', {word(fileId(stream))});
  }
  int flush(std::FILE *stream) override {
    event('U', {word(fileId(stream))});
    return errors ? -1 : 0;
  }
  int get(std::FILE *stream) override {
    const int value = nextSample < samples.size() ? samples[nextSample++] : -1;
    event('G', {word(fileId(stream)), word(static_cast<std::uint32_t>(value))});
    return value;
  }
  void notify(PinStateObserver *target, int number, int value) override {
    event('N',
          {word(observerId(target)), word(static_cast<std::uint32_t>(number)),
           word(static_cast<std::uint32_t>(value))});
  }
  void log(const char *message) override { event('L', {hex(message)}); }
};

extern "C" void inputPinNativeD1(InputPin *);
extern "C" void inputPinNativeD0(InputPin *);
extern "C" void inputPinNativeC2(InputPin *, int, PinStateObserver *) asm(
    "_ZN8Presonus5Panel8InputPinC2EiPNS0_16PinStateObserverE");
extern "C" void
inputPinNativeD2(InputPin *) asm("_ZN8Presonus5Panel8InputPinD2Ev");
static void *deleteTarget = nullptr;
static FakeIO *deleteIO = nullptr;
extern "C" void __real__ZdlPv(void *);
extern "C" void __real__ZdlPvm(void *, std::size_t);
extern "C" void __wrap__ZdlPv(void *pointer) {
  if (pointer == deleteTarget && deleteIO)
    deleteIO->event('X', {});
  __real__ZdlPv(pointer);
}
extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) {
  if (pointer == deleteTarget && deleteIO)
    deleteIO->event('X', {});
  __real__ZdlPvm(pointer, size);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0, deleting = 0, complete = 0, base = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    std::string op;
    unsigned role, observer, failOpen, errors;
    std::uint32_t pin;
    std::array<std::uint32_t, 5> before{}, after{};
    row >> op >> role;
    for (auto &v : before)
      row >> v;
    row >> pin >> observer >> failOpen >> errors;
    for (auto &v : after)
      row >> v;
    std::string expected;
    row >> expected;
    if (!row)
      return 3;
    FakeIO io;
    io.failOpen = failOpen;
    io.errors = errors;
    void *storage = ::operator new(sizeof(InputPin));
    io.pin = static_cast<InputPin *>(storage);
    auto *previous =
        presonus::surface_panel_port::setInputPinConstructionIO(&io);
    if (op == "C1" || op == "C2") {
      if (op == "C1")
        new (storage) InputPin(static_cast<std::int32_t>(pin),
                               FakeIO::observer(observer));
      else
        inputPinNativeC2(io.pin, static_cast<std::int32_t>(pin),
                         FakeIO::observer(observer));
      if (io.state() != after ||
          (io.trace.empty() ? "-" : hex(io.trace)) != expected) {
        std::fprintf(stderr, "Constructor mismatch %u %s role%u\n", cases,
                     op.c_str(), role);
        return 1;
      }
      io.quiet = true;
      inputPinNativeD1(io.pin);
      ::operator delete(storage);
    } else {
      new (storage) InputPin(-1, nullptr);
      InputPinAccess::bind(*io.pin, io, static_cast<std::int32_t>(before[0]),
                           static_cast<std::int32_t>(before[1]),
                           static_cast<std::int32_t>(before[2]),
                           FakeIO::file(before[3]),
                           FakeIO::observer(before[4]));
      io.snapshot = io.state();
      io.frozen = true; // No member access after object lifetime ends.
      deleteTarget = storage;
      deleteIO = &io;
      if (op == "D0") {
        inputPinNativeD0(io.pin);
        ++deleting;
      } else if (op == "D1") {
        inputPinNativeD1(io.pin);
        ++complete;
      } else if (op == "D2") {
        inputPinNativeD2(io.pin);
        ++base;
      } else
        return 4;
      deleteTarget = nullptr;
      deleteIO = nullptr;
      if (io.snapshot != after ||
          (io.trace.empty() ? "-" : hex(io.trace)) != expected) {
        std::fprintf(
            stderr, "Destructor mismatch %u %s role%u trace%s expected%s\n",
            cases, op.c_str(), role, hex(io.trace).c_str(), expected.c_str());
        return 1;
      }
      if (op != "D0")
        ::operator delete(storage);
    }
    presonus::surface_panel_port::setInputPinConstructionIO(previous);
    ++cases;
  }
  if (!input.eof() || cases == 0 || !deleting || !complete || !base)
    return 5;
  std::printf("PASS: %u original ARM InputPin lifetime cases; actual vtable "
              "D1=%u D0=%u, named D2=%u\n",
              cases, complete, deleting, base);
}
