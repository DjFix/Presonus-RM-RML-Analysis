#pragma once
#include "presonus/dice/packet_services.hpp"
#include "presonus/dice/programmer_device_services.hpp"
#include "presonus/dice/response_services.hpp"
namespace Core::Threads {
class Lock;
}
namespace Presonus::DICE {
class Dice3Uart;
}
namespace presonus::dice {
// Independent required borrowed runtime; no default success or legacy Core.
class SubsystemRuntime {
public:
  virtual ~SubsystemRuntime() = default;
  virtual void bind(Presonus::DICE::Dice3Subsystem &,
                    Presonus::DICE::Dice3Uart &) = 0;
  virtual std::unique_ptr<ProgrammerOutputPin> makeResetPin() = 0;
  virtual void sleepMilliseconds(std::uint32_t milliseconds) = 0;
};
// Scoped per-thread pre-construction setup. Borrowed runtime must outlive every
// subsystem created under it. Original ownership/configuration is unresolved.
class ScopedSubsystemRuntime {
public:
  explicit ScopedSubsystemRuntime(SubsystemRuntime &runtime);
  ~ScopedSubsystemRuntime();
  ScopedSubsystemRuntime(const ScopedSubsystemRuntime &) = delete;
  ScopedSubsystemRuntime &operator=(const ScopedSubsystemRuntime &) = delete;

private:
  SubsystemRuntime *previous_;
};
SubsystemRuntime &requireSubsystemRuntime();
// Real UART post/idle + existing receiver acknowledgement + real CCL timing.
class CclSubsystemRuntime final : public SubsystemRuntime,
                                  public SubsystemServices,
                                  public IdlePump {
public:
  explicit CclSubsystemRuntime(ProgrammerDeviceServices &device,
                               Core::Threads::Lock *stateLock = nullptr)
      : stateLock_(stateLock), device_(device), response_(*this) {}
  void bind(Presonus::DICE::Dice3Subsystem &,
            Presonus::DICE::Dice3Uart &) override;
  std::unique_ptr<ProgrammerOutputPin> makeResetPin() override;
  void sleepMilliseconds(std::uint32_t milliseconds) override;
  void post(Presonus::DICE::SysexPacket &) override;
  std::uint32_t waitAck(Presonus::DICE::Dice3Subsystem &,
                        std::int64_t) override;
  void onIdle(bool force) override;

private:
  // Borrowed actual CCL lock: immutable after pre-publication setup.
  Core::Threads::Lock *stateLock_;
  ProgrammerDeviceServices &device_;
  CclResponseServices response_;
  Presonus::DICE::Dice3Uart *uart_ = nullptr;
};
} // namespace presonus::dice
