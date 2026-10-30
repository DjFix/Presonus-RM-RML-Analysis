#include "presonus/dice/manager.hpp"
#include "presonus/dice/manager_lifetime.hpp"
#include "presonus/dice/manager_programmer_services.hpp"
#include "presonus/dice/manager_services.hpp"
#include "presonus/dice/programmer.hpp"
#include "presonus/dice/programmer_device_services.hpp"
#include "presonus/dice/programmer_services.hpp"
#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/panel/uart_comm.hpp"
#include <cstring>
#include <optional>
#include <stdexcept>
#include <utility>

namespace presonus::dice {
namespace {
thread_local std::shared_ptr<ManagerLifetimeConfiguration> configuration;
int integerWord(std::uint32_t value) {
  static_assert(sizeof(int) == sizeof(value));
  int result;
  std::memcpy(&result, &value, sizeof(result));
  return result;
}
class SubsystemRoutes final : public RouteSink {
public:
  void bind(Presonus::DICE::Dice3Subsystem &receiver) { receiver_ = &receiver; }
  std::int32_t setRoute(const RouteTuple &route) override {
    if (!receiver_)
      throw std::logic_error("Manager route receiver is not published");
    return receiver_->setRoute(
        static_cast<Presonus::DICE::Dice3AudioSinkDevice>(
            integerWord(route.sinkDevice)),
        static_cast<Presonus::DICE::Dice3AudioSink>(integerWord(route.sink)),
        static_cast<Presonus::DICE::Dice3AudioSourceDevice>(
            integerWord(route.sourceDevice)),
        static_cast<Presonus::DICE::Dice3AudioSource>(
            integerWord(route.source)));
  }

private:
  Presonus::DICE::Dice3Subsystem *receiver_ = nullptr;
};
class GuardedProgrammer final : public ManagerProgrammerServices {
public:
  GuardedProgrammer(ProgrammerServices &runtime,
                    ProgrammerDeviceServices &device,
                    Presonus::DICE::Dice3Subsystem &receiver,
                    ProgressSink *progress)
      : runtime_(runtime), device_(device), receiver_(receiver),
        progress_(progress) {}
  void prepare(Presonus::DICE::Dice3Programmer &programmer) override {
    if (programmer.inspectState().listener && !progress_)
      throw std::logic_error(
          "Non-null firmware listener requires ProgressSink");
    programmer.bindProgrammerServices(runtime_, -1);
    programmer.bindProgrammerDeviceServices(device_);
    if (progress_)
      programmer.bindProgressSink(*progress_);
  }
  void invalidateSubsystemInfo() override {
    receiver_.markPortableInfoPending();
  }

private:
  ProgrammerServices &runtime_;
  ProgrammerDeviceServices &device_;
  Presonus::DICE::Dice3Subsystem &receiver_;
  ProgressSink *progress_;
};
class CclOwnedRuntime final : public ManagerOwnedRuntime {
public:
  CclOwnedRuntime(Presonus::DICE::Dice3Manager &manager,
                  std::shared_ptr<ProgressSink> progress,
                  std::shared_ptr<ProgrammerDeviceServices> device,
                  std::shared_ptr<presonus::panel::UartServices> uart)
      : managerServices_(static_cast<Core::Threads::Thread &>(manager)),
        programmerRuntime_(transport_),
        device_(device ? std::move(device)
                       : std::make_shared<LinuxProgrammerDeviceServices>()),
        subsystemRuntime_(*device_, &stateLock_),
        progress_(std::move(progress)),
        uart_(uart ? std::move(uart)
                   : std::shared_ptr<presonus::panel::UartServices>(
                         &presonus::panel::systemUartServices(),
                         [](presonus::panel::UartServices *) {})) {}
  std::shared_ptr<presonus::panel::UartServices> uartServices() override {
    return uart_;
  }
  ManagerServices &managerServices() override { return managerServices_; }
  SubsystemRuntime &subsystemRuntime() override { return subsystemRuntime_; }
  void bindChild(Presonus::DICE::Dice3Subsystem &receiver) override {
    routes_.bind(receiver);
    programmer_.emplace(programmerRuntime_, *device_, receiver,
                        progress_.get());
  }
  RouteSink &routeSink() override { return routes_; }
  ManagerProgrammerServices &programmerServices() override {
    if (!programmer_)
      throw std::logic_error("Manager programmer receiver is not published");
    return *programmer_;
  }

private:
  // This lock and all providers are retained until after worker join/child
  // destruction. Shared ownership of this context outlives caller setup.
  Core::Threads::Lock stateLock_;
  CclManagerServices managerServices_;
  LinuxProgrammerTransport transport_;
  CclProgrammerServices programmerRuntime_;
  std::shared_ptr<ProgrammerDeviceServices> device_;
  CclSubsystemRuntime subsystemRuntime_;
  std::shared_ptr<ProgressSink> progress_;
  std::shared_ptr<presonus::panel::UartServices> uart_;
  SubsystemRoutes routes_;
  std::optional<GuardedProgrammer> programmer_;
};
} // namespace

ScopedManagerLifetimeConfiguration::ScopedManagerLifetimeConfiguration(
    std::shared_ptr<ManagerLifetimeConfiguration> next)
    : previous_(configuration) {
  if (!next)
    throw std::invalid_argument("Manager lifetime configuration is required");
  configuration = std::move(next);
}
ScopedManagerLifetimeConfiguration::~ScopedManagerLifetimeConfiguration() {
  configuration = std::move(previous_);
}
std::shared_ptr<ManagerOwnedRuntime>
makeConfiguredManagerRuntime(Presonus::DICE::Dice3Manager &manager) {
  if (!configuration)
    throw std::logic_error("Manager requires scoped lifetime configuration");
  auto owner = configuration->create(manager);
  if (!owner)
    throw std::logic_error("Manager configuration returned no runtime owner");
  return owner;
}
CclManagerLifetimeConfiguration::CclManagerLifetimeConfiguration(
    std::shared_ptr<ProgressSink> progress,
    std::shared_ptr<ProgrammerDeviceServices> device,
    std::shared_ptr<presonus::panel::UartServices> uart)
    : progress_(std::move(progress)), device_(std::move(device)),
      uart_(std::move(uart)) {}
std::shared_ptr<ManagerOwnedRuntime>
CclManagerLifetimeConfiguration::create(Presonus::DICE::Dice3Manager &manager) {
  return std::make_shared<CclOwnedRuntime>(manager, progress_, device_, uart_);
}
} // namespace presonus::dice
