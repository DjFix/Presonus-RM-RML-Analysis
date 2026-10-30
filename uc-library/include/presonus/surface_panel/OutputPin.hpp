#pragma once
#include <cstddef>
#include <cstdio>

namespace Presonus::Panel {
class OutputPin;
}
namespace presonus::surface_panel_port {
// Independent injected boundary, not a recovered libc/Core API or device
// driver.
struct OutputPinIO {
  virtual ~OutputPinIO() = default;
  virtual std::FILE *open(const char *path, const char *mode) = 0;
  virtual int printPin(std::FILE *file, const char *format, int pin) = 0;
  virtual int close(std::FILE *file) = 0;
  virtual void formatPath(char *output, std::size_t capacity,
                          const char *format, int pin) = 0;
  virtual std::size_t write(const void *data, std::size_t size,
                            std::size_t count, std::FILE *file) = 0;
  virtual int buffering(std::FILE *file, char *buffer, int mode,
                        std::size_t size) = 0;
  virtual int put(int character, std::FILE *file) = 0;
  virtual int error() = 0;
  virtual void log(const char *message) = 0;
  virtual void logSet(const char *format, int result, int error) = 0;
};
struct OutputPinAccess;
} // namespace presonus::surface_panel_port
namespace Presonus::Panel {
// Partial preconfigured source port; no historical lifecycle/object ABI.
// Original C++ return declarations remain unproved and pending.
class OutputPin {
public:
  OutputPin(int pin);
  virtual ~OutputPin();
  int setup(int pin);
  void set(int value);

private:
  friend struct presonus::surface_panel_port::OutputPinAccess;
  presonus::surface_panel_port::OutputPinIO *io_ = nullptr;
  int pin_ = 0;
  std::FILE *file_ = nullptr;
  int state_ = 0;
};
} // namespace Presonus::Panel
namespace presonus::surface_panel_port {
struct OutputPinAccess {
  static void bind(Presonus::Panel::OutputPin &pin, OutputPinIO &io, int number,
                   int state, std::FILE *file) {
    pin.io_ = &io;
    pin.pin_ = number;
    pin.state_ = state;
    pin.file_ = file;
  }
  static int number(const Presonus::Panel::OutputPin &pin) { return pin.pin_; }
  static int state(const Presonus::Panel::OutputPin &pin) { return pin.state_; }
  static std::FILE *file(const Presonus::Panel::OutputPin &pin) {
    return pin.file_;
  }
};
} // namespace presonus::surface_panel_port
