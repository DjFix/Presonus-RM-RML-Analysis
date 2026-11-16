#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
namespace Presonus::Surface {
class PresetsPageComponent;
// Partial source port. Original bases, lifecycle, field declarations, return
// spelling and ARM ABI remain unresolved. This borrows the distinct extra
// Scenes collection, not MappablePageComponent's base alias collection.
class ScenesPageComponent {
public:
  struct SourcePortConstruction {};
  ScenesPageComponent(SourcePortConstruction,
                      const Core::Vector<Core::Portable::Parameter *> &extra)
      : extraParameters(extra) {}
  ScenesPageComponent(SourcePortConstruction,
                      const Core::Vector<Core::Portable::Parameter *> &extra,
                      Core::Portable::Component *parameters,
                      PresetsPageComponent &presets)
      : extraParameters(extra), selectionParameters_(parameters),
        presets_(&presets) {}
  // Return declaration remains provisional; recall uses the actual canonical
  // Presets provider through explicitly borrowed source-port composition.
  void rowSelected();
  // Provisional void return; stable collection and object lifetimes required.
  void disconnectMappables();

private:
  const Core::Vector<Core::Portable::Parameter *> &extraParameters;
  Core::Portable::Component *selectionParameters_ = nullptr;
  PresetsPageComponent *presets_ = nullptr;
};
} // namespace Presonus::Surface
