#pragma once
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/OutputComponent.hpp"
#include <cstdint>
#include <vector>

namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
// CCL-backed lifecycle source ports. Native D1 writes its own two vtable words
// and calls Component D2; compiler emits host vptr transitions and real pinned
// Component cleanup. Original secondary base declaration/layout remain unknown.
class GEQLinkHandler : public Core::Portable::Component {
public:
  using Core::Portable::Component::Component;
  ~GEQLinkHandler() override;
};
} // namespace Presonus::Mixer
