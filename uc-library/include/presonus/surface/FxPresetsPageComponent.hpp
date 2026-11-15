#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/corestringbuffer.h"
#include <cstdint>
namespace presonus::surface {
struct FXPageTestAccess;
}
namespace Presonus::Surface {
// Partial initialized source-port model. This does not fabricate the missing
// original PresetsPage constructor or its application dependency providers.
class FxPresetsPageComponent : public Core::Portable::Component {
public:
  explicit FxPresetsPageComponent(std::int32_t channelIndex = 0)
      : channelIndex_(channelIndex) {}
  ~FxPresetsPageComponent() override;
  // Source-port reference return; original declaration remains pending.
  Core::CStringBuffer<256> &getTargetUrl(Core::CStringBuffer<256> &);

private:
  friend struct presonus::surface::FXPageTestAccess;
  Core::Vector<Core::Portable::AliasParam *> aliases_;
  std::int32_t channelIndex_;
};
} // namespace Presonus::Surface
