#pragma once
#include <cstdint>

namespace presonus::dice {
// Independent application services, never declarations of legacy Core APIs.
// UART must already be initialized. No allocation/device-open branch is ported.
class ResponseServices {
public:
  virtual ~ResponseServices() = default;
  virtual std::int64_t clockRawTicks() = 0;
  virtual void pumpIdle(bool force) = 0;
  virtual void sleepMilliseconds(std::uint32_t milliseconds) = 0;
  virtual void timeoutNotice(bool responseSet, std::uint32_t response,
                             std::uint32_t timeoutLowWord) = 0;
};

class IdlePump {
public:
  virtual ~IdlePump() = default;
  virtual void onIdle(bool force) = 0;
};

// Actual CCL Linux source adapter. The borrowed pump is still an explicit
// application transport dependency; this adapter performs no device I/O itself.
class CclResponseServices final : public ResponseServices {
public:
  explicit CclResponseServices(IdlePump &pump) : pump_(pump) {}
  std::int64_t clockRawTicks() override;
  void pumpIdle(bool force) override;
  void sleepMilliseconds(std::uint32_t milliseconds) override;
  void timeoutNotice(bool responseSet, std::uint32_t response,
                     std::uint32_t timeoutLowWord) override;

private:
  IdlePump &pump_;
};
} // namespace presonus::dice
