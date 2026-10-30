#pragma once
#include <cstdint>
#include <memory>

namespace presonus::surface_panel_port {
struct OutputPinIO;
}
namespace presonus::dice {
// Independent required app boundary, not a declaration of original Panel
// construction/destruction or a recovered Core API.
class ProgrammerOutputPin {
public:
  virtual ~ProgrammerOutputPin() = default;
  virtual void set(int value) = 0;
};
class ProgrammerDeviceServices {
public:
  virtual ~ProgrammerDeviceServices() = default;
  virtual std::int32_t openDevice(const char *path, int flags) = 0;
  virtual std::int32_t modeIoctl(std::int32_t descriptor, std::uint32_t request,
                                 std::uint32_t &mode) = 0;
  virtual std::int32_t closeDevice(std::int32_t descriptor) = 0;
  virtual std::unique_ptr<ProgrammerOutputPin> makeOutputPin(int number) = 0;
};
// Real Linux fd/SPI operations and real stdio GPIO provider. The optional
// borrowed IO override supports offline replay and must outlive every pin.
// Program reconstruction tests intercept all device effects; no default
// success.
class LinuxProgrammerDeviceServices final : public ProgrammerDeviceServices {
public:
  explicit LinuxProgrammerDeviceServices(
      presonus::surface_panel_port::OutputPinIO *io = nullptr);
  std::int32_t openDevice(const char *path, int flags) override;
  std::int32_t modeIoctl(std::int32_t descriptor, std::uint32_t request,
                         std::uint32_t &mode) override;
  std::int32_t closeDevice(std::int32_t descriptor) override;
  std::unique_ptr<ProgrammerOutputPin> makeOutputPin(int number) override;

private:
  presonus::surface_panel_port::OutputPinIO &io_;
};
} // namespace presonus::dice
