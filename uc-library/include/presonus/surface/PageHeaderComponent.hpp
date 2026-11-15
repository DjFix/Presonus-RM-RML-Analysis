#pragma once
#include "presonus/MappablePageComponent.hpp"
namespace Presonus::Surface {
// Portable source inheritance; original layout and ordinary return unresolved.
class PageHeaderComponent : public MappablePageComponent {
public:
  explicit PageHeaderComponent(const char *name,
                               Core::Portable::StringParam *label = nullptr)
      : MappablePageComponent(name), label_(label) {}
  void disconnectMappables() override;

private:
  Core::Portable::StringParam *label_; // borrowed, optional
};
} // namespace Presonus::Surface
