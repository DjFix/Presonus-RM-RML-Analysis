#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
#include <memory>
namespace Presonus {
class PageComponent;
}
namespace Presonus::Surface {
class PresetsPageComponent;
// Partial source port. Original bases, lifecycle, field declarations, return
// spelling and ARM ABI remain unresolved. The extra Scenes collection and
// the base alias collection have separate storage.
class ScenesPageComponent {
public:
  struct SourcePortConstruction {};
  ScenesPageComponent(SourcePortConstruction,
                      const Core::Vector<Core::Portable::Parameter *> &extra);
  ScenesPageComponent(SourcePortConstruction,
                      const Core::Vector<Core::Portable::Parameter *> &extra,
                      Core::Portable::Component *parameters,
                      PresetsPageComponent &presets);

  // Own the Presets provider and the extra vector storage. The vector elements
  // and optional selection component still have external lifetimes.
  struct OwnPresetsPage {};
  ScenesPageComponent(OwnPresetsPage,
                      const Core::Vector<Core::Portable::Parameter *> &extra,
                      Core::Portable::Component *parameters,
                      std::unique_ptr<PresetsPageComponent> presets);
  virtual ~ScenesPageComponent();
  // Return declaration remains provisional; recall uses the actual canonical
  // Presets provider through explicitly borrowed source-port composition.
  void rowSelected();
  // Independent borrowed visibility input for the callback's page predicate.
  void bindPage(const Presonus::PageComponent &page) { page_ = &page; }
  // Provisional void return. Forward through the canonical Presets provider.
  void paramChanged(Core::Portable::Parameter *, int);
  // Provisional void return; stable collection and object lifetimes required.
  void disconnectMappables();

private:
  // Reverse member destruction releases the extra storage before Presets
  // destroys its alias storage and CCL Component-managed children.
  std::unique_ptr<PresetsPageComponent> ownedPresets_;
  Core::Vector<Core::Portable::Parameter *> ownedExtraParameters_;
  const Core::Vector<Core::Portable::Parameter *> &extraParameters;
  Core::Portable::Component *selectionParameters_ = nullptr;
  PresetsPageComponent *presets_ = nullptr;
  const Presonus::PageComponent *page_ = nullptr;
};
} // namespace Presonus::Surface
