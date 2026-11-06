#include "presonus/mixer/ChannelParameterController.hpp"
namespace Presonus::Mixer {
ChannelParameterController::ChannelParameterController(
    ChannelComponent &channel, int index)
    : Core::Portable::Component("channel"), channel_(channel), index_(index) {}
} // namespace Presonus::Mixer
