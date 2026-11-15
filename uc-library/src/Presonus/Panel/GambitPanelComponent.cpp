#include "presonus/panel/GambitPanelComponent.hpp"

namespace Presonus::Panel {
// Original D1/D2 delegates to RackPanelComponent; compiler-emitted D0 also
// deallocates. Compile this translation unit with -fno-sized-deallocation to
// preserve the observed unsized global-delete boundary. No ARM layout claim.
GambitPanelComponent::~GambitPanelComponent() = default;
} // namespace Presonus::Panel
