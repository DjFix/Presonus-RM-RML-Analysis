#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdio>

namespace Presonus::Panel {
// Original root interface: one pure callback slot, no virtual destructor.
// The portable void return remains declaration-pending.
class PinStateObserver {
public:
  virtual void pinStateChanged(int pin, int value) = 0;
};
class InputPin;
} // namespace Presonus::Panel
namespace presonus::surface_panel_port {
// Independent injected libc/observer/log gateway. No hardware implementation
// or original observer/Core class definition is supplied.
struct InputPinIO {
  virtual ~InputPinIO() = default;
  virtual std::FILE *open(const char *path, const char *mode) = 0;
  virtual int printPin(std::FILE *file, const char *format, int pin) = 0;
  virtual int close(std::FILE *file) = 0;
  virtual void formatPath(char *output, std::size_t capacity,
                          const char *format, int pin) = 0;
  virtual std::size_t write(const void *data, std::size_t size,
                            std::size_t count, std::FILE *file) = 0;
  virtual int buffering(std::FILE *file, char *buffer, int mode,
                        std::size_t size) = 0;
  virtual void rewind(std::FILE *file) = 0;
  virtual int flush(std::FILE *file) = 0;
  virtual int get(std::FILE *file) = 0;
  virtual void notify(Presonus::Panel::PinStateObserver *observer, int pin,
                      int value) = 0;
  virtual void log(const char *message) = 0;
};
struct InputPinAccess;
// Independent construction gateway: null selects the actual stdio provider.
// Thread-local override must outlive constructed objects; no original API
// claim.
InputPinIO *setInputPinConstructionIO(InputPinIO *io);
InputPinIO &inputPinConstructionIO();
} // namespace presonus::surface_panel_port

namespace Presonus::Panel {
// Portable source class with the evidenced root virtual destructor.
// Native fields/pointers are not an ARM32 layout or ABI claim.
// Ordinary return declaration spellings remain explicitly unresolved.
class InputPin {
public:
  explicit InputPin(int pin = -1, PinStateObserver *observer = nullptr);
  virtual ~InputPin();
  int setup(int pin, PinStateObserver *observer);
  void read();
  void read_debounce();

private:
  friend struct presonus::surface_panel_port::InputPinAccess;
  presonus::surface_panel_port::InputPinIO *io_ = nullptr;
  int pin_ = 0;
  int state_ = 0;
  std::FILE *file_ = nullptr;
  int last_ = 0;
  PinStateObserver *observer_ = nullptr;
};
} // namespace Presonus::Panel

namespace presonus::surface_panel_port {
struct InputPinAccess {
  static void bind(Presonus::Panel::InputPin &pin, InputPinIO &io, int number,
                   int state, int last, std::FILE *file,
                   Presonus::Panel::PinStateObserver *observer) {
    pin.io_ = &io;
    pin.pin_ = number;
    pin.state_ = state;
    pin.last_ = last;
    pin.file_ = file;
    pin.observer_ = observer;
  }
  static int number(const Presonus::Panel::InputPin &pin) { return pin.pin_; }
  static int state(const Presonus::Panel::InputPin &pin) { return pin.state_; }
  static int last(const Presonus::Panel::InputPin &pin) { return pin.last_; }
  static std::FILE *file(const Presonus::Panel::InputPin &pin) {
    return pin.file_;
  }
  static auto *observer(const Presonus::Panel::InputPin &pin) {
    return pin.observer_;
  }
};
} // namespace presonus::surface_panel_port
