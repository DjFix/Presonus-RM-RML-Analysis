#pragma once
#include "core/portable/coreparaminfo.h"
namespace presonus::mixer_parameter_info {
// Independent immutable source-port data. Not original local ELF exports or ARM
// ABI.
extern const Core::Portable::ParamInfo Gate[10];
extern const Core::Portable::ParamInfo Compressor[10];
} // namespace presonus::mixer_parameter_info
