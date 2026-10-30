#pragma once
#include <cstdint>

namespace Core::Threads {
class Thread;
}
namespace presonus::dice {
// Independent source-port boundary, never a declaration of legacy CoreThread.
class ManagerServices {
public:
  virtual ~ManagerServices() = default;
  virtual std::int64_t clockRawTicks() = 0;
  virtual void sleepMilliseconds(std::uint32_t milliseconds) = 0;
  virtual void terminateThread() = 0;
};

// Borrow the actual CCL thread associated with the manager's entry point.
// Original default construction, startup and ownership remain unrecovered.
class CclManagerServices final : public ManagerServices {
public:
  explicit CclManagerServices(Core::Threads::Thread &thread)
      : thread_(thread) {}
  std::int64_t clockRawTicks() override;
  void sleepMilliseconds(std::uint32_t milliseconds) override;
  void terminateThread() override;

private:
  Core::Threads::Thread &thread_;
};
} // namespace presonus::dice
