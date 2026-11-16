#pragma once
#include "presonus/surface/MixerPageComponent.hpp"
namespace Presonus::Surface {
// Partial portable lifecycle model. The tag is independent construction, not
// an original constructor or evidence of original inheritance/ARM layout.
class AssignEditPageComponent : public MixerPageComponent {
public:
  struct SourcePortConstruction {};
  explicit AssignEditPageComponent(SourcePortConstruction)
      : MixerPageComponent() {}
  ~AssignEditPageComponent() override;
  Core::Vector<Core::Portable::AliasParam *> &sourcePortAliases() {
    return aliases_;
  }
};
} // namespace Presonus::Surface
