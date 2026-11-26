#pragma once

namespace Core::Portable {
class Parameter;
}

namespace Presonus::UC {
struct ParamRangeEvent;
}

namespace ParamHelper {
// Portable declaration for the observed callable scope.
void applyRange(Core::Portable::Parameter *parameter,
                const Presonus::UC::ParamRangeEvent &event);
} // namespace ParamHelper
