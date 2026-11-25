#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/registrar_group_registry.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>
#include <memory>
#include <vector>

int main() {
  using namespace Presonus::Panel;
  using Core::Portable::NumericParam;
  using Core::Portable::ParamInfo;
  presonus::panel_binding::RegistrarGroupRegistry registry;
  ControlRegistrar registrar(registry);
  FrontPanelComponent component(FrontPanelComponent::SourcePortConstruction{});
  component.bindControlRegistrar(registrar);
  std::vector<std::unique_ptr<ParamInfo>> infos;
  std::vector<std::unique_ptr<NumericParam>> params;
  std::vector<std::unique_ptr<Control>> controls;
  std::vector<std::unique_ptr<ControlGroup>> groups;
  int groupCount;
  std::cin >> groupCount;
  for (int g = 0; g < groupCount; ++g) {
    int groupId, count;
    std::cin >> groupId >> count;
    auto &group =
        *groups.emplace_back(std::make_unique<ControlGroup>(groupId, 0));
    registry.groups.add(&group);
    for (int i = 0; i < count; ++i) {
      int tag, kind, bound, parameterTag;
      std::cin >> tag >> kind >> bound >> parameterTag;
      if (!kind) {
        group.add(nullptr);
        continue;
      }
      auto &control = *controls.emplace_back(std::make_unique<Control>(tag));
      group.add(&control);
      if (bound) {
        auto &info = *infos.emplace_back(std::make_unique<ParamInfo>());
        info.tag = parameterTag;
        info.type = ParamInfo::kFloat;
        auto &param =
            *params.emplace_back(std::make_unique<NumericParam>(info));
        control.setParameter(&param, 0);
      }
    }
  }
  if (!std::cin)
    return 1;
  std::cout << component.getFaderStyle() << '\n';
}
