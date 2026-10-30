#pragma once
#include "core/portable/corecomponent.h"
namespace presonus::surface_update {
// Independent shared source-port helpers, never original ELF identities.
void setCallbackText(Core::Portable::Component &, const char *, const char *);
void setCallbackAlert(Core::Portable::Component &, const char *, const char *,
                      const char *);
} // namespace presonus::surface_update
