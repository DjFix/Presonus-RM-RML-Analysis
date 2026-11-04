#include "presonus/surface/MappingComponent.hpp"
namespace Presonus::Surface {
Core::Portable::Parameter *MappingComponent::getParamByTag(int tag) const {
  return getParameterByTag(tag);
}
Core::Portable::Parameter *
MappingComponent::getMainScreenParamByTag(int tag) const {
  return mainScreenParameters_ ? mainScreenParameters_->getParameterByTag(tag)
                               : nullptr;
}
} // namespace Presonus::Surface
