#include "presonus/surface/FXEditPageComponent.hpp"
namespace Presonus::Surface {
FXEditPageComponent::~FXEditPageComponent() {
  const int count = observed_.count();
  for (int i = 0; i < count; ++i)
    observed_.at(i)->removeObserver(this);
  observed_.resize(0);
}
void FXEditPageComponent::disconnectMappables() {
  const int count = mappables_.count();
  for (int i = 0; i < count; ++i) {
    // Actual CCL typed-object cast replaces firmware C++ RTTI. Stable
    // initialized containers are the validated domain; callback-driven mutation
    // is excluded.
    if (auto *alias = Core::Portable::AliasParam::cast(mappables_.at(i)))
      alias->setOriginal(nullptr);
  }
}
} // namespace Presonus::Surface
