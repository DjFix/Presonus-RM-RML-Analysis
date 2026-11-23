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
  // Source-port void declarations; original ordinary returns are unresolved.
  void updateVisibility();
  void updateAliasTargets();
  // Source-port callback; the original return declaration remains unresolved.
  void onShow(bool);
  void paramChanged(Core::Portable::Parameter *, int) override;
  Core::Vector<Core::Portable::AliasParam *> &sourcePortAliases() {
    return aliases_;
  }
};
} // namespace Presonus::Surface
