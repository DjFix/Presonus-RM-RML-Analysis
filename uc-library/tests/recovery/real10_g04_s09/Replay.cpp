#include "presonus/surface/StChannelSettingsPageComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
struct OtherController : Core::Portable::ParamObserverBase {
  void paramChanged(Core::Portable::Parameter *, int) override {}
};
struct Observer : Core::Portable::ParamObserverBase {
  int edits = 0, changes = 0;
  void paramChanged(Core::Portable::Parameter *, int message) override {
    if (message == Core::Portable::Parameter::kEdit)
      ++edits;
    if (message == Core::Portable::Parameter::kChanged)
      ++changes;
  }
};
std::uint32_t bits(float v) {
  std::uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}
struct Product : Presonus::Surface::StChannelSettingsPageComponent {
  Product() : StChannelSettingsPageComponent(SourcePortConstruction{}) {}
  int edits = 0;
  void paramChanged(Core::Portable::Parameter *p, int msg) override {
    if (p->getTag() == 1000 && msg == Core::Portable::Parameter::kEdit)
      ++edits;
    StChannelSettingsPageComponent::paramChanged(p, msg);
  }
};
int main() {
  int message, nameKind, originalKind, controllerKind, available;
  while (std::cin >> message >> nameKind >> originalKind >> controllerKind >>
         available) {
    Product product;
    Core::Portable::ParamInfo destinationInfo =
        PARAM_FLOAT(1000, "result", 0, 1, .25f, 0, nullptr, nullptr, 0, 0);
    product.addParameters(&destinationInfo, 1);
    const char *name = nameKind == 0   ? "ch_select"
                       : nameKind == 1 ? "other"
                                       : "";
    Core::Portable::ParamInfo aliasInfo =
        PARAM_ALIAS(1, "", Core::Portable::ParamInfo::kStorable);
    std::strncpy(aliasInfo.name, name, sizeof aliasInfo.name - 1);
    Core::Portable::AliasParam input(aliasInfo);
    Core::Portable::Component source;
    Core::Portable::ParamInfo capabilityInfo =
        PARAM_FLOAT(360, "capability", 0, 1, 0, 0, nullptr, nullptr, 0, 0);
    if (available)
      source.addParameters(&capabilityInfo, 1);
    Core::Portable::ParamInfo originalInfo =
        PARAM_FLOAT(2, "source", 0, 1, 0, 0, nullptr, nullptr, 0, 0);
    Core::Portable::NumericParam original(originalInfo);
    OtherController other;
    if (controllerKind == 1)
      original.setController(&other);
    if (controllerKind == 2)
      original.setController(&source);
    if (originalKind)
      input.setOriginal(&original);
    auto *dest = product.getParameterByTag(1000);
    Observer observer;
    dest->addObserver(&observer);
    product.paramChanged(&input, message);
    // Independent provider-only observation: actual CCL
    // alias/controller/type-ID conversion and actual tag360 lookup, followed by
    // actual NumericParam edit.
    auto *observedOriginal = input.getOriginal();
    auto *observedController =
        observedOriginal ? observedOriginal->getController() : nullptr;
    auto *observedComponent =
        Core::Portable::core_cast<Core::Portable::Component>(
            observedController);
    Core::Portable::NumericParam baseline(destinationInfo);
    Observer baselineController;
    baseline.setController(&baselineController);
    Observer baselineObserver;
    baseline.addObserver(&baselineObserver);
    baseline.setValue(available ? 1.f : 0.f, true);
    std::cout << (product.needsSave() ? 1 : 0) << " " << bits(dest->getValue())
              << " " << product.edits << " " << observer.changes << " "
              << int(observedOriginal != nullptr) << " "
              << int(observedController != nullptr) << " "
              << int(observedComponent != nullptr) << " "
              << int(observedComponent &&
                     observedComponent->getParameterByTag(360))
              << " " << bits(baseline.getValue()) << " "
              << baselineController.edits << " " << baselineObserver.changes
              << "\n";
    dest->removeObserver(&observer);
    baseline.removeObserver(&baselineObserver);
    input.setOriginal(nullptr);
    original.setController(nullptr);
  }
}
