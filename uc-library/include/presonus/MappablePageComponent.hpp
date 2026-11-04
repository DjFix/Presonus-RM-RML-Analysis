#pragma once
#include "core/portable/corecomponent.h"
#include "presonus/IMainScreenPageController.hpp"
namespace Presonus {
// Intentional source port with actual CCL ownership. Original private layout,
// ordinary return spelling, constructor identity and ARM ABI remain unresolved.
class MappablePageComponent : public Core::Portable::Component,
                              public IMainScreenPageController {
public:
  explicit MappablePageComponent(const char *name) : Component(name) {}
  const char *getPageName() const override;
  bool connectParameter(const char *, Core::Portable::Parameter *) override;
  void disconnectMappables() override;
  // Independent setup: CCL ParamList owns parameters; vector borrows aliases.
  Core::Portable::AliasParam &addMappable(int tag, const char *name) {
    auto *p = static_cast<Core::Portable::AliasParam *>(
        paramList.addAlias(tag, name));
    aliases_.add(p);
    return *p;
  }

private:
  Core::Vector<Core::Portable::AliasParam *> aliases_;
};
} // namespace Presonus
