#include "presonus/dsp/ControlSuspender.hpp"
namespace Presonus::Dsp {
ControlSuspender::ControlSuspender(BorrowedAudioHALTag, IAudioHAL &hal)
    : hal_(hal), previous_(hal.suspendControlSurfaces(true)) {}
ControlSuspender::~ControlSuspender() {
  if (previous_ == 0)
    hal_.suspendControlSurfaces(false);
}
} // namespace Presonus::Dsp
