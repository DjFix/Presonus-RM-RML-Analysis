#include "presonus/surface_panel/OutputPin.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using Presonus::Panel::OutputPin;
using presonus::surface_panel_port::OutputPinAccess;
using presonus::surface_panel_port::OutputPinIO;
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
struct FakeOutputIO final : OutputPinIO {
  OutputPin *pin = nullptr;
  unsigned failOpen = 0, openCount = 0;
  bool errors = false, returnExpected = false;
  int putResult = 0, errorValue = 0;
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
  std::array<std::uint32_t, 3> state() const {
    return {static_cast<std::uint32_t>(OutputPinAccess::number(*pin)),
            static_cast<std::uint32_t>(OutputPinAccess::state(*pin)),
            fileId(OutputPinAccess::file(*pin))};
  }
  void event(char kind, const std::vector<std::string> &args) {
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
  int put(int character, std::FILE *stream) override {
    event('P', {word(fileId(stream)), word(character)});
    return returnExpected ? character : putResult;
  }
  int error() override {
    event('E', {word(static_cast<std::uint32_t>(errorValue))});
    return errorValue;
  }
  void log(const char *message) override { event('L', {hex(message)}); }
  void logSet(const char *format, int result, int error) override {
    event('X', {hex(format), word(static_cast<std::uint32_t>(result)),
                word(static_cast<std::uint32_t>(error))});
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    char operation;
    unsigned role, failOpen, errors, expectedReturn;
    std::uint32_t argument, result, error, expectedStatus;
    std::array<std::uint32_t, 3> before{}, after{};
    row >> operation >> role;
    for (auto &value : before)
      row >> value;
    row >> argument >> failOpen >> errors >> expectedReturn >> result >>
        error >> expectedStatus;
    for (auto &value : after)
      row >> value;
    std::string expectedTrace;
    row >> expectedTrace;
    if (!row)
      return 3;
    FakeOutputIO io;
    OutputPin pin(-1);
    io.pin = &pin;
    io.failOpen = failOpen;
    io.errors = errors != 0;
    io.returnExpected = expectedReturn != 0;
    io.putResult = static_cast<std::int32_t>(result);
    io.errorValue = static_cast<std::int32_t>(error);
    OutputPinAccess::bind(pin, io, static_cast<std::int32_t>(before[0]),
                          static_cast<std::int32_t>(before[1]),
                          FakeOutputIO::file(before[2]));
    std::uint32_t status = 0;
    if (operation == 'S')
      status = static_cast<std::uint32_t>(
          pin.setup(static_cast<std::int32_t>(argument)));
    else if (operation == 'V')
      pin.set(static_cast<std::int32_t>(argument));
    else
      return 4;
    if (io.state() != after || status != expectedStatus ||
        hex(io.trace) != expectedTrace) {
      std::fprintf(stderr,
                   "Mismatch case %u op %c role %u status %u/%u\ntrace "
                   "%s\nexpected %s\n",
                   cases, operation, role, status, expectedStatus,
                   hex(io.trace).c_str(), expectedTrace.c_str());
      return 1;
    }
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 5;
  std::printf("PASS: %u original ARM OutputPin state/IO contract cases\n",
              cases);
}
