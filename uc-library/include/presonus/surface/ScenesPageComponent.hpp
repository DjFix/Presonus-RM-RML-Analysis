#pragma once
#include "core/portable/coreparams.h"
#include "core/public/corevector.h"
namespace Presonus::Surface {
// Partial source port. Original bases, lifecycle, field declarations, return
// spelling and ARM ABI remain unresolved. This borrows the distinct extra
// Scenes collection, not MappablePageComponent's base alias collection.
class ScenesPageComponent {
public:
  struct SourcePortConstruction {};
  ScenesPageComponent(SourcePortConstruction,
                      const Core::Vector<Core::Portable::Parameter *> &extra)
      : extraParameters(extra) {}
  // Provisional void return; stable collection and object lifetimes required.
  void disconnectMappables();

private:
  const Core::Vector<Core::Portable::Parameter *> &extraParameters;
};
} // namespace Presonus::Surface
