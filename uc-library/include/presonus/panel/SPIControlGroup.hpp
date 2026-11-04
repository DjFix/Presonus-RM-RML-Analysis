#pragma once
#include "core/public/corevector.h"
#include "presonus/surface_panel/ControlGroup.hpp"
#include <array>
#include <cstdint>
namespace presonus::spi_port {
// Independent transport boundary. LinuxTransfer submits an SPI_IOC_MESSAGE;
// ownership and opening of the descriptor remain with the caller.
struct Transfer {
  virtual ~Transfer() = default;
  virtual void submit(int descriptor, std::uint32_t request,
                      const std::uint8_t *transmit, std::uint8_t *receive,
                      int length) = 0;
};
class LinuxTransfer final : public Transfer {
public:
  void submit(int descriptor, std::uint32_t request,
              const std::uint8_t *transmit, std::uint8_t *receive,
              int length) override;
};
} // namespace presonus::spi_port
namespace Presonus::Panel {
// Portable source model using the actual ControlGroup implementation. Original
// ARM layout, complete virtual interfaces and binary interoperability
// unresolved.
class SPIControlGroup : public ControlGroup {
public:
  SPIControlGroup(int groupId, int groupArgument, int byteCount);
  // Independent borrowed-word/transport API retained for source-port callers.
  SPIControlGroup(const Core::ConstVector<std::uint32_t> &controls,
                  int byteCount, int descriptor,
                  presonus::spi_port::Transfer &transfer);
  void onIdle();
  void markDirty(bool value) { dirty = value; }
  bool isDirty() const { return dirty; }
  int transportDescriptor() const { return descriptor; }
  int payloadByteCount() const { return byteCount; }
  // Explicit source-port attachment; neither constructor performs device I/O.
  void attachTransport(int fd, presonus::spi_port::Transfer &provider) {
    descriptor = fd;
    transfer = &provider;
  }
  const std::array<std::uint8_t, 5> &transmitted() const { return transmit; }
  const std::array<std::uint8_t, 5> &received() const { return receive; }

private:
  // Null selects the inherited ControlGroup; a borrowed vector is never copied
  // into an unrelated second control collection.
  const Core::ConstVector<std::uint32_t> *borrowedWords = nullptr;
  int byteCount;
  int descriptor;
  presonus::spi_port::Transfer *transfer;
  bool dirty = false;
  std::array<std::uint8_t, 5> transmit{};
  std::array<std::uint8_t, 5> receive{};
};
} // namespace Presonus::Panel
