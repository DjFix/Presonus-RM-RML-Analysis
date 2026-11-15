#pragma once
#include "core/portable/coreparaminfo.h"
#include <cstdint>
namespace presonus::panel {
// Independent typed source-port adapter. Address identifies an original table,
// never a host pointer or an assertion of original C++ declaration/layout.
const Core::Portable::ParamInfo *
panelParameterTable(std::uint32_t originalAddress);
} // namespace presonus::panel
