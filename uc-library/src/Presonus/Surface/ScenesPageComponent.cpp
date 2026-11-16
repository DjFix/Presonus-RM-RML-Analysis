#include "presonus/surface/ScenesPageComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
namespace Presonus::Surface {
void ScenesPageComponent::rowSelected() {
  if (selectionParameters_)
    if (auto *parameter = selectionParameters_->getParameterByTag(12))
      if (parameter->getValue() > 0.f)
        presets_->recall();
}
void ScenesPageComponent::disconnectMappables() {
  const int count = extraParameters.count();
  for (int i = 0; i < count; ++i)
    if (auto *parameter = extraParameters[i])
      // Intentional adaptation from original C++ RTTI to actual CCL type IDs.
      if (auto *alias = Core::Portable::AliasParam::cast(parameter))
        alias->setOriginal(nullptr);
}
} // namespace Presonus::Surface
