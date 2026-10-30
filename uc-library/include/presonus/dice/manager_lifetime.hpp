#pragma once
#include <memory>
namespace Presonus::DICE {
class Dice3Manager;
class Dice3Subsystem;
} // namespace Presonus::DICE
namespace presonus::panel {
class UartServices;
}
namespace presonus::dice {
class ManagerServices;
class SubsystemRuntime;
class RouteSink;
class ManagerProgrammerServices;
class ProgressSink;
class ProgrammerDeviceServices;
// Independent runtime owner. Real production factory provides actual CCL/Linux
// services; explicit test configurations remain visibly separate.
class ManagerOwnedRuntime {
public:
  virtual ~ManagerOwnedRuntime() = default;
  virtual std::shared_ptr<presonus::panel::UartServices> uartServices() = 0;
  virtual ManagerServices &managerServices() = 0;
  virtual SubsystemRuntime &subsystemRuntime() = 0;
  virtual void bindChild(Presonus::DICE::Dice3Subsystem &) = 0;
  virtual RouteSink &routeSink() = 0;
  virtual ManagerProgrammerServices &programmerServices() = 0;
};
class ManagerLifetimeConfiguration {
public:
  virtual ~ManagerLifetimeConfiguration() = default;
  virtual std::shared_ptr<ManagerOwnedRuntime>
  create(Presonus::DICE::Dice3Manager &) = 0;
};
class ScopedManagerLifetimeConfiguration {
public:
  explicit ScopedManagerLifetimeConfiguration(
      std::shared_ptr<ManagerLifetimeConfiguration>);
  ~ScopedManagerLifetimeConfiguration();
  ScopedManagerLifetimeConfiguration(
      const ScopedManagerLifetimeConfiguration &) = delete;
  ScopedManagerLifetimeConfiguration &
  operator=(const ScopedManagerLifetimeConfiguration &) = delete;

private:
  std::shared_ptr<ManagerLifetimeConfiguration> previous_;
};
std::shared_ptr<ManagerOwnedRuntime>
makeConfiguredManagerRuntime(Presonus::DICE::Dice3Manager &);
// Real source-based production configuration. Optional listener bridge must
// outlive use; non-null firmware listeners require a valid ProgressSink.
class CclManagerLifetimeConfiguration final
    : public ManagerLifetimeConfiguration {
public:
  explicit CclManagerLifetimeConfiguration(
      std::shared_ptr<ProgressSink> progress = {},
      std::shared_ptr<ProgrammerDeviceServices> device = {},
      std::shared_ptr<presonus::panel::UartServices> uart = {});
  std::shared_ptr<ManagerOwnedRuntime>
  create(Presonus::DICE::Dice3Manager &) override;

private:
  std::shared_ptr<ProgressSink> progress_;
  std::shared_ptr<ProgrammerDeviceServices> device_;
  std::shared_ptr<presonus::panel::UartServices> uart_;
};
} // namespace presonus::dice
