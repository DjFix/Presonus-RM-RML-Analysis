#pragma once
#include "presonus/surface/MixerPageComponent.hpp"
namespace Presonus::Surface {
// Partial portable lifecycle model. The tag is independent construction, not
// an original constructor or evidence of original inheritance/ARM layout.
class FirmwarePageComponent : public MixerPageComponent {
public:
  struct SourcePortConstruction {};
  explicit FirmwarePageComponent(SourcePortConstruction)
      : MixerPageComponent() {}
  ~FirmwarePageComponent() override;
  Core::Vector<Core::Portable::AliasParam *> &sourcePortAliases() {
    return aliases_;
  }
};
} // namespace Presonus::Surface
