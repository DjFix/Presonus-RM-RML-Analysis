#include "presonus/surface/TBRoutingPageComponent.hpp"
#include <cstdint>
#include <cstring>
namespace Presonus::Surface {
TBRoutingPageComponent::~TBRoutingPageComponent() = default;
void TBRoutingPageComponent::connectChannel(
    const Core::Portable::Component *channel, int index, bool) {
  auto wrappedTag = [index](std::uint32_t delta) {
    std::uint32_t bits = static_cast<std::uint32_t>(index) + delta;
    std::int32_t result;
    std::memcpy(&result, &bits, sizeof result);
    return result;
  };
  if (auto *alias =
          Core::Portable::AliasParam::cast(paramList.byTag(wrappedTag(0x76))))
    alias->setOriginal(channel->getParameterByTag(0x12e));
  if (auto *alias =
          Core::Portable::AliasParam::cast(paramList.byTag(wrappedTag(0x78))))
    alias->setOriginal(channel->getParameterByTag(0x12c));
}
void TBRoutingPageComponent::disconnectMappables() {
  const int count = mappables_.count();
  for (int i = 0; i < count; ++i)
    if (auto *alias = Core::Portable::AliasParam::cast(mappables_[i]))
      alias->setOriginal(nullptr);
}
} // namespace Presonus::Surface
