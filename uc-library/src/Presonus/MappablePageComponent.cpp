#include "presonus/MappablePageComponent.hpp"
namespace Presonus {
const char *MappablePageComponent::getPageName() const { return getName(); }
bool MappablePageComponent::connectParameter(const char *name,
                                             Core::Portable::Parameter *p) {
  auto *alias = Core::Portable::AliasParam::cast(paramList.find(name));
  if (!alias)
    return false;
  alias->setOriginal(p);
  return true;
}
void MappablePageComponent::disconnectMappables() {
  for (int i = 0; i < aliases_.count(); ++i)
    aliases_[i]->setOriginal(nullptr);
}
} // namespace Presonus
