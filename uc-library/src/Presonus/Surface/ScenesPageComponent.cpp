#include "presonus/surface/ScenesPageComponent.hpp"
#include "presonus/PageComponent.hpp"
#include "presonus/surface/PresetsPageComponent.hpp"
#include <cstring>
#include <stdexcept>
#include <utility>

namespace Presonus::Surface {
ScenesPageComponent::ScenesPageComponent(
    SourcePortConstruction,
    const Core::Vector<Core::Portable::Parameter *> &extra)
    : extraParameters(extra) {}

ScenesPageComponent::ScenesPageComponent(
    SourcePortConstruction,
    const Core::Vector<Core::Portable::Parameter *> &extra,
    Core::Portable::Component *parameters, PresetsPageComponent &presets)
    : extraParameters(extra), selectionParameters_(parameters),
      presets_(&presets) {}

ScenesPageComponent::ScenesPageComponent(
    OwnPresetsPage, const Core::Vector<Core::Portable::Parameter *> &extra,
    Core::Portable::Component *parameters,
    std::unique_ptr<PresetsPageComponent> presets)
    : ownedPresets_(std::move(presets)), ownedExtraParameters_(extra),
      extraParameters(ownedExtraParameters_), selectionParameters_(parameters),
      presets_(ownedPresets_.get()) {
  if (!presets_)
    throw std::invalid_argument("owned Scenes construction requires Presets");
}

ScenesPageComponent::~ScenesPageComponent() = default;

void ScenesPageComponent::rowSelected() {
  if (selectionParameters_)
    if (auto *parameter = selectionParameters_->getParameterByTag(12))
      if (parameter->getValue() > 0.f)
        presets_->recall();
}
void ScenesPageComponent::paramChanged(Core::Portable::Parameter *parameter,
                                       int message) {
  if (!presets_)
    return;

  presets_->PresetsPageComponent::paramChanged(parameter, message);
  if (page_ && page_->isVisible() &&
      message == Core::Portable::Parameter::kChanged &&
      std::strcmp(parameter->getName(), "fsw_load") == 0 &&
      parameter->getValue() > 0.f)
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
