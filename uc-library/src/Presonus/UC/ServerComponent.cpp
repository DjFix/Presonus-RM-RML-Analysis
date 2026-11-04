#include "presonus/uc/ServerComponent.hpp"
namespace Presonus::UC {
// Native body resets the base vtables then delegates to Component cleanup.
// The real C++ base destructor invokes pinned upstream child/parameter cleanup.
ServerComponent::~ServerComponent() = default;
} // namespace Presonus::UC
