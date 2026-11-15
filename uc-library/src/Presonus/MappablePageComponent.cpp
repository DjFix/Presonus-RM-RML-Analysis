#include "presonus/MappablePageComponent.hpp"
namespace Presonus {
void *MappablePageComponent::castTo(int classId) {
  return classId == 1835102288 || classId == 1348560741 || classId == 1131375984
             ? this
             : nullptr;
}
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
