#include "core/system/coredebug.h"
#include "presonus/surface_panel/OutputPin.hpp"
#include <cerrno>
namespace presonus::surface_panel_port {
namespace {
class LibcOutputPinIO final : public OutputPinIO {
public:
  std::FILE *open(const char *p, const char *m) override {
    return std::fopen(p, m);
  }
  int printPin(std::FILE *f, const char *fmt, int pin) override {
    return std::fprintf(f, fmt, pin);
  }
  int close(std::FILE *f) override { return std::fclose(f); }
  void formatPath(char *p, std::size_t n, const char *fmt, int pin) override {
    std::snprintf(p, n, fmt, pin);
  }
  std::size_t write(const void *d, std::size_t s, std::size_t n,
                    std::FILE *f) override {
    return std::fwrite(d, s, n, f);
  }
  int buffering(std::FILE *f, char *b, int m, std::size_t n) override {
    return std::setvbuf(f, b, m, n);
  }
  int put(int c, std::FILE *f) override { return std::fputc(c, f); }
  int error() override { return errno; }
  void log(const char *message) override { Core::DebugPrint(message); }
  void logSet(const char *format, int result, int error) override {
    Core::DebugPrintf(format, result, error);
  }
};
LibcOutputPinIO actualLibc;
} // namespace
} // namespace presonus::surface_panel_port
namespace Presonus::Panel {
OutputPin::OutputPin(int pin)
    : io_(&presonus::surface_panel_port::actualLibc), pin_(pin), file_(nullptr),
      state_(-1) {
  if (pin >= 0)
    setup(pin);
}
OutputPin::~OutputPin() {
  if (file_)
    io_->close(file_);
}
} // namespace Presonus::Panel
