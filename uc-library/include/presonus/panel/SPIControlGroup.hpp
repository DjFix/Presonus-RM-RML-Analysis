#pragma once
#include "core/public/corevector.h"
#include <array>
#include <cstdint>
namespace presonus::spi_port {
// Required independent app boundary. Implementations own their device/transport
// policy; this source port never opens or programs hardware.
struct Transfer {
  virtual ~Transfer() = default;
  virtual void submit(int descriptor, std::uint32_t request,
                      const std::uint8_t *transmit, std::uint8_t *receive,
                      int length) = 0;
};
} // namespace presonus::spi_port
namespace Presonus::Panel {
// Portable state chosen for source integration, not original ARM layout or
// control declarations. Controls expose observed zero/nonzero words as values.
class SPIControlGroup {
public:
  SPIControlGroup(const Core::ConstVector<std::uint32_t> &controls,
                  int byteCount, int descriptor,
                  presonus::spi_port::Transfer &transfer);
  void onIdle();
  // Independent source-port state configuration and inspection.
  void markDirty(bool value) { dirty = value; }
  bool isDirty() const { return dirty; }
  const std::array<std::uint8_t, 5> &transmitted() const { return transmit; }
  const std::array<std::uint8_t, 5> &received() const { return receive; }

private:
  const Core::ConstVector<std::uint32_t> &controls;
  int byteCount;
  int descriptor;
  presonus::spi_port::Transfer &transfer;
  bool dirty = false;
  std::array<std::uint8_t, 5> transmit{};
  std::array<std::uint8_t, 5> receive{};
};
} // namespace Presonus::Panel
