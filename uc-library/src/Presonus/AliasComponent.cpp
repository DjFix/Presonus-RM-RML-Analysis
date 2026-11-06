#include "presonus/AliasComponent.hpp"

#include <cstring>
#include <memory>
#include <stdexcept>

namespace Presonus {

AliasComponent::AliasComponent(const char *name)
    : Core::Portable::Component(name), original(nullptr) {}

AliasComponent::AliasComponent(const char *name,
                               Core::Portable::Component &component)
    : Core::Portable::Component(name), original(nullptr) {
  setOriginal(&component);
}

void AliasComponent::setOriginal(Core::Portable::Component *component) {
  using namespace Core::Portable;
  if (original) {
    for (int index = countParameters() - 1; index >= 0; --index) {
      if (auto *parameter = getParameterAt(index)) {
        paramList.remove(parameter);
        delete parameter;
      }
    }
  }
  original = component;
  if (!original)
    return;
  const int count = original->countParameters();
  for (int index = 0; index < count; ++index) {
    auto *parameter = original->getParameterAt(index);
    if (!parameter)
      continue;
    // The firmware uses an 84-byte stack ParamInfo. Use the actual pinned CCL
    // structure and its owned copy instead; never reproduce native-size writes
    // into a host structure or the unbounded firmware strcpy.
    ParamInfo info{};
    info.type = ParamInfo::kAlias;
    info.tag = parameter->getTag();
    const char *name = parameter->getName();
    const auto length = ::strnlen(name, sizeof(info.name));
    if (length == sizeof(info.name))
      throw std::length_error(
          "AliasComponent parameter name is not terminated");
    std::memcpy(info.name, name, length + 1);
    auto alias = std::make_unique<AliasParam>(info, true);
    const int previousCount = countParameters();
    paramList.add(alias.get());
    // The provider's void add() discards Vector::add's allocation result.
    // Keep ownership until insertion is observed; portable failure adaptation.
    if (countParameters() != previousCount + 1)
      throw std::bad_alloc();
    auto *added = alias.release(); // ParamList owns the actual provider object.
    added->setOriginal(parameter);
    added->enable(parameter->isEnabled());
  }
}

Core::Portable::Component *AliasComponent::getOriginal() const {
  return original;
}

void AliasComponent::paramChanged(Core::Portable::Parameter *parameter,
                                  int message) {
  Core::Portable::Component::paramChanged(parameter, message);
}

} // namespace Presonus
