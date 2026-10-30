#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corebuffer.h"
#include "core/public/corevector.h"
#include "core/system/corethread.h"
#include "presonus/dice/sysex.hpp"
#include "presonus/panel/uart_comm.hpp"
#include <array>
#include <cstdint>
#include <memory>

namespace presonus::dice {
struct UartOwnedState;
struct UartLifetimeAccess;
enum class AssemblyError : unsigned {
  none,
  mutexOverlap,
  nullInput,
  invalidReceiver,
  receiverStorageChanged,
  invalidReceiverCount,
  invalidTransportWriteLength,
  invalidTransportReadLength
};
class PacketLogSink {
public:
  virtual ~PacketLogSink() = default;
  virtual void log(const Presonus::DICE::SysexPacket &) = 0;
};
class AssemblyCallbacks {
public:
  virtual ~AssemblyCallbacks() = default;
  virtual void noReceiver(unsigned type) = 0;
  virtual void packetLog(const Presonus::DICE::SysexPacket &) = 0;
  virtual void sourcePortError(AssemblyError, unsigned value) = 0;
};
class CclAssemblyCallbacks final : public AssemblyCallbacks {
public:
  explicit CclAssemblyCallbacks(PacketLogSink &sink) : sink_(sink) {}
  void noReceiver(unsigned type) override;
  void packetLog(const Presonus::DICE::SysexPacket &) override;
  void sourcePortError(AssemblyError, unsigned value) override;

private:
  PacketLogSink &sink_;
};

// Independent seeded source-port state, never an original this-object layout.
// The whole67-byte pre-mutex span is retained: receive[64], disabled,
// padding[2]. To model C1 use count0 and span[64]=0; C1 does not initialize
// other span bytes.
class UartAssemblyState {
public:
  UartAssemblyState(const std::array<unsigned char, 67> &spanSeed,
                    unsigned char countSeed, int receiverCapacity);
  UartAssemblyState(const UartAssemblyState &) = delete;
  UartAssemblyState &operator=(const UartAssemblyState &) = delete;
  unsigned char *span() {
    return static_cast<unsigned char *>(storage_.getAddress());
  }
  const unsigned char *span() const {
    return static_cast<const unsigned char *>(storage_.getAddress());
  }
  unsigned char count = 0;
  AssemblyError error = AssemblyError::none;
  unsigned rejectedUnsafeWrites = 0;
  Core::Threads::Lock lock;
  Core::Vector<Presonus::DICE::ISysexReceiver *> receivers;

private:
  Core::IO::Buffer storage_;
};
} // namespace presonus::dice

namespace Presonus::DICE {
// RTTI proves both original public, nonvirtual bases; no ARM layout claim.
class Dice3Uart : public Core::Portable::Singleton<Dice3Uart>,
                  public Presonus::Panel::UARTComm {
public:
  // Default original-identity constructor; storage remains an independent port.
  Dice3Uart();
  ~Dice3Uart() override;
  // Independent borrowed setup API, separate from the default owned path.
  Dice3Uart(presonus::dice::UartAssemblyState &state,
            presonus::dice::AssemblyCallbacks &callbacks);
  // CANDIDATE void: ordinary return spellings remain declaration-pending.
  void post(SysexPacket &packet);
  void idleRead();
  void onIdle();
  void release();
  // CANDIDATE void. Original non-template return spelling is unencoded.
  void assembleSYSEX(unsigned char *data, int length);
  // CANDIDATE void: original return declarations remain unencoded.
  void registerReceiver(ISysexReceiver *receiver);
  void unRegisterReceiver(ISysexReceiver *receiver);

private:
  // Independent bits for observed ARM +0x44 gate. Original static type/meaning
  // unresolved; this is distinct from the inherited UART descriptor at +0x40.
  std::uint32_t closeGateBits_ = 0xffffffffu;
  std::unique_ptr<presonus::dice::UartOwnedState> owned_;
  presonus::dice::UartAssemblyState &state_;
  presonus::dice::AssemblyCallbacks &callbacks_;
  friend struct presonus::dice::UartLifetimeAccess;
};
} // namespace Presonus::DICE

namespace presonus::dice {
// Independent setup/fixture access; no original field names or ABI asserted.
struct UartLifetimeAccess {
  static UartAssemblyState &state(Presonus::DICE::Dice3Uart &uart) {
    return uart.state_;
  }
  static bool ownsState(const Presonus::DICE::Dice3Uart &uart) {
    return bool(uart.owned_);
  }
  static const void *ownedAddress(const Presonus::DICE::Dice3Uart &uart) {
    return uart.owned_.get();
  }
  static std::uint32_t gate(const Presonus::DICE::Dice3Uart &uart) {
    return uart.closeGateBits_;
  }
  static void gate(Presonus::DICE::Dice3Uart &uart, std::uint32_t bits) {
    uart.closeGateBits_ = bits;
  }
};
} // namespace presonus::dice
