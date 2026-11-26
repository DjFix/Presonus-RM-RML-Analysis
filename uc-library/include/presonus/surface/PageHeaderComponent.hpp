#pragma once
#include "presonus/MappablePageComponent.hpp"
namespace Presonus {
class AssignmentHandlerTable;
}
namespace Presonus::Surface {
// Portable source inheritance; original layout and ordinary return unresolved.
class PageHeaderComponent : public MappablePageComponent {
public:
  explicit PageHeaderComponent(const char *name,
                               Core::Portable::StringParam *label = nullptr)
      : MappablePageComponent(name), label_(label) {}
  // Source-port setup. The focus table and parameters are borrowed.
  PageHeaderComponent(const char *name, Core::Portable::AliasParam *focus,
                      Core::Portable::StringParam *label,
                      AssignmentHandlerTable &assignments)
      : MappablePageComponent(name), label_(label), focus_(focus),
        assignments_(&assignments) {}
  void disconnectMappables() override;
  // Provisional void return. Original return declaration remains unresolved.
  void updateFocusParam(Core::Portable::Parameter *parameter);

private:
  Core::Portable::StringParam *label_; // borrowed, optional
  Core::Portable::AliasParam *focus_ = nullptr;
  AssignmentHandlerTable *assignments_ = nullptr;
};
} // namespace Presonus::Surface
