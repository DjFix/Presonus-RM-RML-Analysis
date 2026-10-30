#pragma once
#include "core/public/corestringbuffer.h"

namespace presonus::utilities {
// Independent exported wrappers around original internal-linkage app helpers.
// These declarations do not establish the original unencoded return types.
void removeWhitespace(Core::CStringBuffer<256> &text);
void makeProperMixedCase(Core::CStringBuffer<256> &text);
} // namespace presonus::utilities
