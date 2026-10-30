#pragma once
#include "core/portable/coresingleton.h"
#include "core/public/corebuffer.h"
#include "core/public/corevector.h"
#include "core/system/corethread.h"
#include "presonus/noaa/spi_service.hpp"
#include "presonus/noaa/sysex_packet.hpp"
#include "presonus/surface_panel/InputPin.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <optional>

namespace Presonus::NOAA {
// Original table has two pure slots, receive then accepts, no virtual dtor.
// Return spellings below are portable candidates, not recovered declarations.
class ISysexReceiver {
public:
  virtual void receive(const SysexPacket &) = 0;
  virtual bool accepts(const SysexPacket &) = 0;

protected:
  ~ISysexReceiver() = default;
};
} // namespace Presonus::NOAA

namespace presonus::noaa {
enum class SpiPacketError {
  none,
  nullInput,
  receiveOverflow,
  invalidReceiver,
  receiverStorageChanged,
  invalidReceiverCount
};
// Independent state, not the original ARM this layout or hardware constructor.
// Genuine CCL services; no fake Core/PinStateObserver implementation.
class SpiPacketState {
public:
  SpiPacketState(const std::array<unsigned char, 256> &seed,
                 std::uint32_t countSeed, unsigned char disabledSeed,
                 int receiverCapacity)
      : count(countSeed), disabled(disabledSeed), receivers(receiverCapacity),
        storage_(256) {
    std::memcpy(span(), seed.data(), seed.size());
  }
  unsigned char *span() {
    return static_cast<unsigned char *>(storage_.getAddress());
  }
  const unsigned char *span() const {
    return static_cast<const unsigned char *>(storage_.getAddress());
  }
  std::uint32_t count;
  unsigned char disabled;
  SpiPacketError error = SpiPacketError::none;
  unsigned rejectedUnsafeWrites = 0;
  Core::Threads::Lock lock;
  Core::Vector<Presonus::NOAA::ISysexReceiver *> receivers;

private:
  Core::IO::Buffer storage_;
};
} // namespace presonus::noaa

namespace Presonus::NOAA {
// Portable source composition of the evidenced primary Singleton and
// secondary one-slot observer. Native layout/adjusting thunk differs from ARM.
class TCardSPI : public Core::Portable::Singleton<TCardSPI>,
                 public Presonus::Panel::PinStateObserver {
public:
  TCardSPI();
  ~TCardSPI() override;
  // Independent borrowed-state setup; not the original default constructor.
  explicit TCardSPI(presonus::noaa::SpiPacketState &state)
      : state_(state), io_(&presonus::noaa::spiServiceConstructionIO()) {}
  // Portable return spellings below remain declaration-pending.
  int open(const char *path);
  void post(SysexPacket &packet);
  void idleRead();
  void idleReadPin();
  void onIdle(bool readSpi);
  void pinStateChanged(int pin, int value) override;
  void assembleSYSEX(unsigned char *data, int length);
  void registerReceiver(ISysexReceiver *receiver);
  void unRegisterReceiver(ISysexReceiver *receiver);
  void release();

private:
  friend struct presonus::noaa::SpiServiceAccess;
  std::optional<presonus::noaa::SpiPacketState> ownedState_;
  presonus::noaa::SpiPacketState &state_;
  presonus::noaa::SpiServiceIO *io_;
  int descriptor_ = -1;
  std::array<Presonus::Panel::InputPin *, 32> pins_{};
  unsigned pinCount_ = 0;
  unsigned rejectedTransferResults_ = 0;
};
} // namespace Presonus::NOAA

namespace presonus::noaa {
// Independent test/source-port access, not an original recovered API.
struct SpiServiceAccess {
  static void bind(Presonus::NOAA::TCardSPI &spi, SpiServiceIO &io, int fd,
                   const std::array<Presonus::Panel::InputPin *, 32> &pins,
                   unsigned count) {
    spi.io_ = &io;
    spi.descriptor_ = fd;
    spi.pins_ = pins;
    spi.pinCount_ = count;
  }
  static int descriptor(const Presonus::NOAA::TCardSPI &spi) {
    return spi.descriptor_;
  }
  static unsigned pinCount(const Presonus::NOAA::TCardSPI &spi) {
    return spi.pinCount_;
  }
  static auto *pin(const Presonus::NOAA::TCardSPI &spi, unsigned i) {
    return spi.pins_.at(i);
  }
  static unsigned rejected(const Presonus::NOAA::TCardSPI &spi) {
    return spi.rejectedTransferResults_;
  }
  static auto *singleton() { return Presonus::NOAA::TCardSPI::theInstance; }
  static void singleton(Presonus::NOAA::TCardSPI *spi) {
    Presonus::NOAA::TCardSPI::theInstance = spi;
  }
  static SpiPacketState &state(Presonus::NOAA::TCardSPI &spi) {
    return spi.state_;
  }
};
} // namespace presonus::noaa
