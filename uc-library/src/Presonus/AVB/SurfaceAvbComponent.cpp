#include "presonus/avb/SurfaceAvbComponent.hpp"
namespace Presonus::AVB {
// Compiler emits original D1/D2 variants. Actual pinned Component::~Component
// performs child/array/parameter cleanup; no original Core instructions
// execute.
SurfaceAvbComponent::~SurfaceAvbComponent() {}
} // namespace Presonus::AVB
