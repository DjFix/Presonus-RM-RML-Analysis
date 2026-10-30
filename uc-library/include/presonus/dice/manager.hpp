#pragma once
#include "core/portable/coresingleton.h"
#include "core/system/corethread.h"
#include "presonus/dice/manager_services.hpp"
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>

namespace Presonus::UC {
class IFirmwareUpdateListener;
}

namespace presonus::dice {
class ManagerProgrammerServices;
class ManagerOwnedRuntime;
class ManagerWorkerGuard;
// Independent raw-word transport boundary corresponding to the original
// Dice3Subsystem::setRoute call. This does not implement UART, wait or timing.
struct RouteTuple {
  std::uint32_t sinkDevice, sink, sourceDevice, source;
};
class RouteSink {
public:
  virtual ~RouteSink() = default;
  virtual std::int32_t setRoute(const RouteTuple &route) = 0;
};
} // namespace presonus::dice

namespace Presonus::DICE {
// Original enum identity is encoded in mangling; original enumerator names
// and underlying declaration are unresolved. Portable domain is int32.
enum Dice3RoutingProfile : int {};
enum Dice3ClockProfile : int {};
enum Dice3SampleRate : int;
class Dice3Subsystem;
class Dice3Uart;

// Independent raw-word storage for the five observed output stores. Original
// member names, declaration/layout and the ordinary return type are unresolved.
struct DiceInfo {
  std::array<std::uint32_t, 5> portableWords{};
};

class Dice3Manager : public Core::Threads::Thread,
                     public Core::Portable::Singleton<Dice3Manager> {
public:
  Dice3Manager();
  ~Dice3Manager() override;
  // Independent borrowed setup: no original worker/child ownership.
  explicit Dice3Manager(presonus::dice::RouteSink &sink);
  void setPortableRouteSink(presonus::dice::RouteSink &sink) {
    portableSink_ = &sink;
  }
  // Explicit portable integer return choice for the observed zero result.
  std::int32_t setDiceRoutingProfile(Dice3RoutingProfile profile);
  std::int32_t setDiceMonitorSource(int side, int sourceDevice, int source);

  void setPortableRuntime(Dice3Subsystem &subsystem, Dice3Uart &uart,
                          presonus::dice::ManagerServices &services) {
    portableSubsystem_ = &subsystem;
    portableUart_ = &uart;
    portableServices_ = &services;
  }
  // CANDIDATE return spellings: ordinary originals do not encode these types.
  std::int32_t setDiceClockRate(Dice3SampleRate rate);
  std::int32_t setDiceClockProfile(Dice3ClockProfile profile);
  std::int32_t getDice3Info(DiceInfo *info);
  std::int32_t threadEntry() override;
  void release();

  // CANDIDATE int32 returns: original ordinary declarations unresolved.
  std::int32_t updateFirmware(UC::IFirmwareUpdateListener *listener,
                              const unsigned char *image, int length);
  std::int32_t eraseFirmware();
  // CANDIDATE ordinary returns remain unresolved.
  std::int32_t resetDice3();
  std::int32_t setDice3Serial(int serial, unsigned char unit);
  void setPortableProgrammerServices(
      presonus::dice::ManagerProgrammerServices &services) {
    portableProgrammerServices_ = &services;
  }

  bool portableWorkerMayDispatch() const {
    return portableReceiverReady_.load(std::memory_order_acquire);
  }

  unsigned char portableStopByte() const {
    return portableStop_.load(std::memory_order_acquire);
  }
  void setPortableStopByte(unsigned char value) {
    portableStop_.store(value, std::memory_order_release);
  }

private:
  friend class presonus::dice::ManagerWorkerGuard;
  void retirePortableReceiver();
  int portableReceiverBaseline_ = 0;
  bool portableReceiverDetached_ = false;
  std::atomic<bool> portableReceiverReady_{true};
  // Real source bases above adapt legacy CoreThread to pinned CCL Thread.
  // Independent storage below is not an original ARM layout.
  std::shared_ptr<presonus::dice::ManagerOwnedRuntime> portableOwner_;
  std::unique_ptr<Dice3Subsystem> ownedSubsystem_;
  presonus::dice::ManagerProgrammerServices *portableProgrammerServices_ =
      nullptr;
  presonus::dice::RouteSink *portableSink_;
  Dice3Subsystem *portableSubsystem_ = nullptr;
  Dice3Uart *portableUart_ = nullptr;
  presonus::dice::ManagerServices *portableServices_ = nullptr;
  // Intentional source-port concurrency adaptation; original is a plain byte.
  std::atomic<unsigned char> portableStop_{0};
  // Declared last: rollback quiescence runs before owner/child teardown.
  std::unique_ptr<presonus::dice::ManagerWorkerGuard> ownedWorker_;
};
} // namespace Presonus::DICE
