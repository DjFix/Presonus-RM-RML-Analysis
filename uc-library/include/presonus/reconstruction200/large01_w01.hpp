#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::AVB {
// Intentional source-port inheritance: the original body calls Component
// cleanup. Original complete layout, secondary vtables and ARM ABI remain
// unresolved.
class SurfaceAvbComponent : public Core::Portable::Component {
public:
  ~SurfaceAvbComponent() override;
};
} // namespace Presonus::AVB
