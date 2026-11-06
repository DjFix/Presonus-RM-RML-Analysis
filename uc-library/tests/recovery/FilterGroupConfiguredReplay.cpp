#include "core/portable/coreparams.h"
#include "presonus/mixer/FilterGroupComponent.hpp"
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace Core::Portable;
namespace {
void require(bool ok) {
  if (!ok)
    throw std::runtime_error("provider state/ownership mismatch");
}
struct TrackedString : StringParam {
  int &destroyed;
  TrackedString(const ParamInfo &info, int &count)
      : StringParam(info), destroyed(count) {}
  ~TrackedString() { ++destroyed; }
};
struct FixtureGroup : Presonus::Mixer::FilterGroupComponent {
  FixtureGroup() : FilterGroupComponent(SourcePortConstruction{}) {}
  void adopt(Parameter *parameter) { paramList.add(parameter); }
};
void lifetime() {
  int destroyed = 0;
  ParamInfo info{};
  info.type = ParamInfo::kString;
  info.tag = 600;
  {
    FixtureGroup group;
    auto *text = new TrackedString(info, destroyed);
    group.adopt(text);
    require(StringParam::cast(group.getParameterByTag(600)) == text);
    text->fromString("live");
    require(group.isConfigured());
    text->fromString("");
    require(!group.isConfigured());
    require(destroyed == 0);
  }
  require(destroyed == 1);
  std::cerr << "real CCL owned derived StringParam: live update and one "
               "destruction\n";
}
} // namespace
int main() {
  lifetime();
  int kind, tag, first, tail, advertised;
  while (std::cin >> kind >> tag >> first >> tail >> advertised) {
    ParamInfo info{};
    info.type = kind == 2 ? ParamInfo::kString : ParamInfo::kFloat;
    info.tag = tag;
    info.maxValue = 1;
    std::strcpy(info.name, "filterName");
    Presonus::Mixer::FilterGroupComponent group(
        Presonus::Mixer::FilterGroupComponent::SourcePortConstruction{});
    if (kind)
      group.addParameters(&info, 1);
    auto *parameter = kind ? group.getParameterAt(0) : nullptr;
    auto *text = StringParam::cast(parameter);
    require((text != nullptr) == (kind == 2));
    char bytes[] = {static_cast<char>(first), static_cast<char>(tail), 0};
    if (text)
      text->fromString(bytes);
    // Mutate only descriptor metadata after construction: runtime class query
    // must continue to follow the actual CCL object, not ParamInfo::type.
    info.type = advertised ? ParamInfo::kString : ParamInfo::kFloat;
    const std::string before =
        text ? static_cast<const char *>(text->getText()) : "";
    const bool result = group.isConfigured();
    require(group.countParameters() == (kind ? 1 : 0));
    require(group.getParameterByTag(600) ==
            (kind && tag == 600 ? parameter : nullptr));
    require((StringParam::cast(parameter) != nullptr) == (kind == 2));
    require(!text || before == static_cast<const char *>(text->getText()));
    std::cout << int(result) << '\n';
  }
}
