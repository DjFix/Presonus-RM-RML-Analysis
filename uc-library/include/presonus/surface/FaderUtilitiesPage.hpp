#pragma once
#include "presonus/MackieControlModel.hpp"
#include "presonus/PageComponent.hpp"
// Intentional partial source-port classes. The application destructor ranges
// only reset dispatch pointers and call Component destruction. Using the real
// pinned provider as a base models that cleanup; original inheritance, complete
// fields, vtable addresses and ARM32 layout are not established.
namespace Presonus::Surface {
class FaderUtilitiesPage : public PageComponent {
public:
  FaderUtilitiesPage() : PageComponent("", nullptr, 0) {}
  FaderUtilitiesPage(const char *formName, int tag);
  ~FaderUtilitiesPage() override;
};
} // namespace Presonus::Surface
