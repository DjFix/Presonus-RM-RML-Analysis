#pragma once
#include "presonus/surface/MixerPageComponent.hpp"
namespace presonus::surface {
struct FXPageTestAccess;
}
namespace Presonus::Surface {
// Initialized portable source model. No original constructor, ARM layout or
// inheritance is claimed. Core providers and the existing portable base are
// real.
class FXEditPageComponent : public MixerPageComponent {
public:
  FXEditPageComponent() = default;
  ~FXEditPageComponent() override;
  // Portable return choice; original unencoded return declaration is
  // unresolved.
  void disconnectMappables();

private:
  friend struct presonus::surface::FXPageTestAccess;
  Core::Vector<Core::Portable::Parameter *> observed_;
  Core::Vector<Core::Portable::Parameter *> mappables_;
};
} // namespace Presonus::Surface
