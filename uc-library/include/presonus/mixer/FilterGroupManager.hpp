#pragma once
#include "core/portable/corecomponent.h"
namespace Presonus::Mixer {
// Intentional CCL 5.0.0 source port. Original ARM layout and complete virtual
// interface are unresolved. Only construction and base cleanup are recovered.
class FilterGroupManager : public Core::Portable::Component {
public:
  explicit FilterGroupManager(const char *name);
  ~FilterGroupManager() override;
};
} // namespace Presonus::Mixer
