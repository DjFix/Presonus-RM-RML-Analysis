#include "core/system/coredebug.h"
#include "presonus/avb/AvbComponent.hpp"
#include <cstring>
namespace Presonus::AVB {
AvbComponent::~AvbComponent() {
  if (state_.resource)
    state_.resource->release();
}
void AvbComponent::configureStaticTalkerStreams() {
  const bool alternate = state_.linkMode == 2;
  auto tx = [this](std::uint32_t tag, std::uint32_t size, std::uint32_t x,
                   std::uint32_t y, std::uint32_t z) {
    services_.sendRoutingPacket({{tag, size, 0, x, y, z}, false});
  };
  tx(0x64746174, 28, 0, alternate ? 40 : 60, 1);
  tx(0x64746174, 28, 2, alternate ? 41 : 61, 1);
  tx(0x64746174, 28, 1, alternate ? 36 : 58, 1);
  tx(0x64746174, 28, 3, 42, state_.consoleSource);
  tx(0x64746174, 28, 26, 62, 1);
  tx(0x64746174, 28, 27, 63, 1);
  tx(0x64746174, 28, 30, 40, 1);
  tx(0x64746174, 28, 31, 41, 1);
  tx(0x64746174, 28, 32, 36, 1);
  tx(0x64746174, 28, 23, 37, 1);
  tx(0x69746176, 24, 24, 1, 40);
  tx(0x69746176, 24, 25, 1, 41);
  tx(0x69746176, 24, 28, 0, 38);
  tx(0x69746176, 24, 29, 0, 39);
}
void AvbComponent::routeLinkSlotsFromAvb() {
  if (!state_.cascade)
    return;
  const auto index = state_.cascade->index;
  Core::DebugPrintf("AvbComponent::routeLinkSlotsFromAvb listener index=%d\n",
                    index);
  auto tx = [this, index](std::uint32_t x, std::uint32_t y, std::uint32_t z) {
    services_.sendRoutingPacket({{0x616c6272, 24, index, x, y, z}, false});
  };
  tx(0, 60, 1);
  tx(2, 61, 1);
  tx(1, 58, 1);
  tx(3, 42, 16);
  tx(26, 62, 2);
}
void AvbComponent::setSpectrumDataTxSource(int source, int channel) {
  if (source == -1)
    services_.sendRoutingPacket({{0x64746174, 28, 0, 23, 37, 1}, false});
  else
    services_.sendRoutingPacket(
        {{0x69746176, 24, 0, 23, static_cast<std::uint32_t>(channel),
          static_cast<std::uint32_t>(source)},
         false});
}
} // namespace Presonus::AVB
