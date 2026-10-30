#include "presonus/surface_panel/InputPin.hpp"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

namespace {
unsigned stage = 0, failStage = 0, nextCharacter = '1';
std::vector<std::string> trace;
std::FILE *file(unsigned id) {
  return reinterpret_cast<std::FILE *>(std::uintptr_t(0x8000 + id * 256));
}
unsigned fileId(std::FILE *stream) {
  for (unsigned i = 1; i <= 3; ++i)
    if (stream == file(i))
      return i;
  std::abort();
}
void require(bool condition) {
  if (!condition)
    std::abort();
}
struct Observer final : Presonus::Panel::PinStateObserver {
  unsigned calls = 0;
  int number = 0, value = 0;
  void pinStateChanged(int pin, int sample) override {
    ++calls;
    number = pin;
    value = sample;
  }
};
} // namespace

extern "C" std::FILE *__wrap_fopen(const char *path, const char *mode) {
  ++stage;
  require(stage <= 3);
  const char *paths[] = {"", "/sys/class/gpio/export",
                         "/sys/class/gpio/gpio34/direction",
                         "/sys/class/gpio/gpio34/value"};
  require(std::strcmp(path, paths[stage]) == 0);
  require(std::strcmp(mode, stage == 3 ? "r" : "a") == 0);
  trace.push_back("open" + std::to_string(stage));
  return stage == failStage ? nullptr : file(stage);
}
extern "C" int __wrap_fprintf(std::FILE *stream, const char *format, ...) {
  require(fileId(stream) == 1 && std::strcmp(format, "%d") == 0);
  va_list args;
  va_start(args, format);
  require(va_arg(args, int) == 34);
  va_end(args);
  trace.push_back("print34");
  return 2;
}
// Actual pinned CCL compilation exposes glibc's fortified fprintf alias at O3.
// Intercept the same test boundary; never pass a fake FILE to glibc.
extern "C" int __wrap___fprintf_chk(std::FILE *stream, int, const char *format,
                                    ...) {
  require(fileId(stream) == 1 && std::strcmp(format, "%d") == 0);
  va_list args;
  va_start(args, format);
  require(va_arg(args, int) == 34);
  va_end(args);
  trace.push_back("print34");
  return 2;
}
extern "C" int __wrap_fclose(std::FILE *stream) {
  trace.push_back("close" + std::to_string(fileId(stream)));
  return 0;
}
extern "C" std::size_t __wrap_fwrite(const void *data, std::size_t size,
                                     std::size_t count, std::FILE *stream) {
  require(fileId(stream) == 2 && size == 1 && count == 2 &&
          std::memcmp(data, "in", 2) == 0);
  trace.push_back("write-in");
  return count;
}
extern "C" int __wrap_setvbuf(std::FILE *stream, char *buffer, int mode,
                              std::size_t size) {
  require(fileId(stream) == 3 && buffer == nullptr && mode == 2 && size == 0);
  trace.push_back("buffer");
  return 0;
}
extern "C" void __wrap_rewind(std::FILE *stream) {
  require(fileId(stream) == 3);
  trace.push_back("rewind");
}
extern "C" int __wrap_fflush(std::FILE *stream) {
  require(fileId(stream) == 3);
  trace.push_back("flush");
  return 0;
}
extern "C" int __wrap_fgetc(std::FILE *stream) {
  require(fileId(stream) == 3);
  trace.push_back("get");
  return int(nextCharacter);
}

int main() {
  using Presonus::Panel::InputPin;
  using presonus::surface_panel_port::InputPinAccess;
  require(presonus::surface_panel_port::setInputPinConstructionIO(nullptr) ==
          nullptr);
  {
    InputPin negative(-1);
    require(stage == 0 && InputPinAccess::file(negative) == nullptr);
  }
  Observer observer;
  {
    InputPin pin(34, &observer);
    require((trace == std::vector<std::string>{"open1", "print34", "close1",
                                               "open2", "write-in", "close2",
                                               "open3", "buffer"}));
    require(InputPinAccess::file(pin) == file(3));
    pin.read();
    require(observer.calls == 1 && observer.number == 34 &&
            observer.value == 1);
    nextCharacter = '0';
    pin.read_debounce();
    require(observer.calls == 2 && observer.value == 0);
  }
  require(trace.back() == "close3");
  std::puts("PASS: actual stdio provider, source CCL logger linkage, typed "
            "observer and cleanup; no device calls");
}
