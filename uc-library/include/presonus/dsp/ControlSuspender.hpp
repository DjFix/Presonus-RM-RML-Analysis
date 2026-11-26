#pragma once
#include "presonus/dsp/audio_hal.hpp"
namespace Presonus::Dsp {
// Independent source-port construction API, not an original ELF constructor.
struct BorrowedAudioHALTag {};
// Caller serializes access and keeps this same HAL alive throughout the guard.
// Provider calls must not throw during destruction. No original layout/ABI
// claim.
class ControlSuspender {
public:
  explicit ControlSuspender(BorrowedAudioHALTag, IAudioHAL &hal);
  ~ControlSuspender();
  ControlSuspender(const ControlSuspender &) = delete;
  ControlSuspender &operator=(const ControlSuspender &) = delete;

private:
  IAudioHAL &hal_;
  std::uint8_t previous_;
};
} // namespace Presonus::Dsp
