#include "core/system/coredebug.h"
#include "presonus/dice/programmer_device_services.hpp"
#include "presonus/surface_panel/OutputPin.hpp"
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>

namespace presonus::dice {
namespace {
class StdioOutputPinIO final : public surface_panel_port::OutputPinIO {
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
  int put(int character, std::FILE *file) override {
    return std::fputc(character, file);
  }
  int error() override { return errno; }
  void log(const char *message) override { Core::DebugPrintf("%s", message); }
  void logSet(const char *format, int result, int error) override {
    Core::DebugPrintf(format, result, error);
  }
};
surface_panel_port::OutputPinIO &defaultPinIO() {
  static StdioOutputPinIO io;
  return io;
}
// Independent borrowed-IO forwarder: clear only the actual member's closed
// FILE field before forwarding fclose. This keeps normal setup/set semantics
// and prevents stale already-closed FILE cleanup if a later IO callback throws.
// The OutputPin member remains the sole teardown owner; this object owns no
// FILE.
class MemberOutputPinIO final : public surface_panel_port::OutputPinIO {
public:
  explicit MemberOutputPinIO(surface_panel_port::OutputPinIO &io) : io_(io) {}
  void attach(Presonus::Panel::OutputPin &pin) { pin_ = &pin; }
  std::FILE *open(const char *p, const char *m) override {
    return io_.open(p, m);
  }
  int printPin(std::FILE *f, const char *fmt, int p) override {
    return io_.printPin(f, fmt, p);
  }
  int close(std::FILE *f) override {
    using A = surface_panel_port::OutputPinAccess;
    if (pin_ && A::file(*pin_) == f)
      A::bind(*pin_, *this, A::number(*pin_), A::state(*pin_), nullptr);
    return io_.close(f);
  }
  void formatPath(char *p, std::size_t n, const char *fmt, int v) override {
    io_.formatPath(p, n, fmt, v);
  }
  std::size_t write(const void *d, std::size_t s, std::size_t n,
                    std::FILE *f) override {
    return io_.write(d, s, n, f);
  }
  int buffering(std::FILE *f, char *b, int m, std::size_t n) override {
    return io_.buffering(f, b, m, n);
  }
  int put(int c, std::FILE *f) override { return io_.put(c, f); }
  int error() override { return io_.error(); }
  void log(const char *m) override { io_.log(m); }
  void logSet(const char *f, int r, int e) override { io_.logSet(f, r, e); }

private:
  surface_panel_port::OutputPinIO &io_;
  Presonus::Panel::OutputPin *pin_ = nullptr;
};
// Independent lifetime adapter around real Panel C1/setup/set/D1 sources.
class OutputPinAdapter final : public ProgrammerOutputPin {
public:
  OutputPinAdapter(surface_panel_port::OutputPinIO &io, int number)
      : io_(io), memberIO_(io_), pin_(-1) {
    memberIO_.attach(pin_);
    surface_panel_port::OutputPinAccess::bind(pin_, memberIO_, number, -1,
                                              nullptr);
    if (number >= 0)
      pin_.setup(number);
  }
  ~OutputPinAdapter() override =
      default; // Actual member destructor owns the FILE.
  void set(int value) override { pin_.set(value); }

private:
  surface_panel_port::OutputPinIO &io_;
  MemberOutputPinIO memberIO_;
  Presonus::Panel::OutputPin pin_;
};
} // namespace

LinuxProgrammerDeviceServices::LinuxProgrammerDeviceServices(
    surface_panel_port::OutputPinIO *io)
    : io_(io != nullptr ? *io : defaultPinIO()) {}
std::int32_t LinuxProgrammerDeviceServices::openDevice(const char *path,
                                                       int flags) {
  return ::open(path, flags);
}
std::int32_t LinuxProgrammerDeviceServices::modeIoctl(std::int32_t descriptor,
                                                      std::uint32_t request,
                                                      std::uint32_t &mode) {
  return ::ioctl(descriptor, static_cast<unsigned long>(request), &mode);
}
std::int32_t
LinuxProgrammerDeviceServices::closeDevice(std::int32_t descriptor) {
  return ::close(descriptor);
}
std::unique_ptr<ProgrammerOutputPin>
LinuxProgrammerDeviceServices::makeOutputPin(int number) {
  return std::make_unique<OutputPinAdapter>(io_, number);
}
} // namespace presonus::dice
