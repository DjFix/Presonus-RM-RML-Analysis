#include "presonus/mixer/ChannelDCAComponent.hpp"
namespace Presonus::Mixer {
// Compiler invokes actual pinned Vector storage and ServerComponent/CCL
// cleanup.
ChannelDCAComponent::~ChannelDCAComponent() = default;
} // namespace Presonus::Mixer
