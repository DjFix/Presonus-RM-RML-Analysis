#include "core/system/coredebug.h"
#include "presonus/surface_panel/InputPin.hpp"

namespace presonus::surface_panel_port {
namespace {
class StdioInputPinIO final : public InputPinIO {
public:
  std::FILE *open(const char *path, const char *mode) override {
    return std::fopen(path, mode);
  }
  int printPin(std::FILE *file, const char *format, int pin) override {
    return std::fprintf(file, format, pin);
  }
  int close(std::FILE *file) override { return std::fclose(file); }
  void formatPath(char *output, std::size_t capacity, const char *format,
                  int pin) override {
    std::snprintf(output, capacity, format, pin);
  }
  std::size_t write(const void *data, std::size_t size, std::size_t count,
                    std::FILE *file) override {
    return std::fwrite(data, size, count, file);
  }
  int buffering(std::FILE *file, char *buffer, int mode,
                std::size_t size) override {
    return std::setvbuf(file, buffer, mode, size);
  }
  void rewind(std::FILE *file) override { std::rewind(file); }
  int flush(std::FILE *file) override { return std::fflush(file); }
  int get(std::FILE *file) override { return std::fgetc(file); }
  void notify(Presonus::Panel::PinStateObserver *observer, int pin,
              int value) override {
    observer->pinStateChanged(pin, value);
  }
  void log(const char *message) override { Core::DebugPrintf("%s", message); }
};
thread_local InputPinIO *overrideIO = nullptr;
} // namespace
InputPinIO *setInputPinConstructionIO(InputPinIO *io) {
  auto *previous = overrideIO;
  overrideIO = io;
  return previous;
}
InputPinIO &inputPinConstructionIO() {
  static StdioInputPinIO provider;
  return overrideIO ? *overrideIO : provider;
}
} // namespace presonus::surface_panel_port

namespace Presonus::Panel {
InputPin::InputPin(int pin, PinStateObserver *observer)
    : io_(&presonus::surface_panel_port::inputPinConstructionIO()), pin_(pin),
      state_(0), file_(nullptr), last_(0), observer_(observer) {
  if (pin >= 0)
    setup(pin, observer);
}
InputPin::~InputPin() {
  if (file_ != nullptr)
    io_->close(file_);
}
} // namespace Presonus::Panel
