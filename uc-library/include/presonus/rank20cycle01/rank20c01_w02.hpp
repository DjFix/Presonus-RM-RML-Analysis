#pragma once
#include "core/portable/corecomponent.h"

namespace Presonus {
// Partial source port. Native D1 restores its interface tables and delegates
// cleanup to Component. Actual CCL supplies that lifecycle here. The remaining
// original interfaces, fields and ARM32 layout are not reconstructed.
class MackieControlUnit : public Core::Portable::Component {
public:
  using Component::Component;
  ~MackieControlUnit() override;
};
} // namespace Presonus
