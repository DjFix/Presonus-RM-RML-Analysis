#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/registrar_group_registry.hpp"
#include "presonus/panel/switch_control.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>
#include <memory>
#include <vector>

int main() {
  using namespace Presonus::Panel;
  presonus::panel_binding::RegistrarGroupRegistry registry;
  ControlRegistrar registrar(registry);
  FrontPanelComponent component(FrontPanelComponent::SourcePortConstruction{});
  component.bindControlRegistrar(registrar);
  std::vector<std::unique_ptr<Control>> controls;
  std::vector<std::unique_ptr<ControlGroup>> groups;
  std::vector<std::pair<Control *, int>> identities;
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
      switch (kind) {
      case 1:
        controls.push_back(std::make_unique<Control>(tag));
        break;
      case 2:
        controls.push_back(std::make_unique<SevenSegControl>(tag));
        break;
      case 3:
        controls.push_back(std::make_unique<SwitchControl>(tag, 0, false));
        break;
      default:
        return 1;
      }
      auto *control = controls.back().get();
      group.add(control);
      identities.emplace_back(control, 1 + 10 * g + i);
    }
  }
  if (!std::cin)
    return 1;
  const auto *result = component.getSevenSegControl();
  if (!result) {
    std::cout << "0\n";
    return 0;
  }
  for (const auto &[control, identity] : identities)
    if (result == control) {
      std::cout << identity << '\n';
      return 0;
    }
  return 1;
}
