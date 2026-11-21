#pragma once
#include "core/portable/corecomponent.h"
#include "core/public/coreproperty.h"
#include "presonus/DspComponent.hpp"
#include <memory>
namespace Presonus::Mixer {
// Partial source port. Real CCL Component and typed queries intentionally
// replace the original intermediate application bases; no original
// lifecycle/layout claim.
class GEQComponent : public Core::Portable::Component {
public:
  // Provisional void return; original declaration remains unresolved.
  void flatten();
  DECLARE_CORE_CLASS(0x171408, GEQComponent, Core::Portable::Component)
  struct SourcePortConstruction {};
  explicit GEQComponent(SourcePortConstruction, const char *name = "")
      : Core::Portable::Component(name) {}
  // Independent source-port ownership. The handler, when present, is a
  // separate instance transferred for disposal through release().
  struct AdoptLifecycle {};
  GEQComponent(AdoptLifecycle, std::unique_ptr<Presonus::DspComponent> dsp,
               Core::IPropertyHandler *handler, const char *name = "");
  ~GEQComponent() override;

private:
  std::unique_ptr<Presonus::DspComponent> dsp_;
  Core::IPropertyHandler *handler_ = nullptr;
};
} // namespace Presonus::Mixer
