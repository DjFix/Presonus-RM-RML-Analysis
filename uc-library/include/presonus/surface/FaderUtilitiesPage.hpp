#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/MackieControlModel.hpp"
// Intentional partial source-port classes. The application destructor ranges
// only reset dispatch pointers and call Component destruction. Using the real
// pinned provider as a base models that cleanup; original inheritance, complete
// fields, vtable addresses and ARM32 layout are not established.
namespace Presonus::Surface {
class FaderUtilitiesPage : public Core::Portable::Component {
public:
  ~FaderUtilitiesPage();
};
} // namespace Presonus::Surface
