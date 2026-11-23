#include "presonus/panel/PanelComponent.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/panel/registrar_group_registry.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"

#include <array>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {
using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
using Presonus::Panel::Control;
using Presonus::Panel::ControlGroup;
using Presonus::Panel::ControlRegistrar;

class FixturePanel final : public Presonus::Panel::PanelComponent {};

bool runCase(int query, int parameterIndex, std::size_t groupCount) {
  // These parameters share metadata and values. Only object identity differs.
  const ParamInfo info{};
  NumericParam a(info), b(info), c(info);
  const std::array<NumericParam *, 3> params{&a, &b, &c};
  std::vector<std::unique_ptr<Control>> controls;
  std::vector<std::unique_ptr<ControlGroup>> groups;
  presonus::panel_binding::RegistrarGroupRegistry roster;
  for (std::size_t i = 0; i < groupCount; ++i) {
    int groupId;
    std::size_t controlCount;
    std::cin >> groupId >> controlCount;
    auto group = std::make_unique<ControlGroup>(groupId, 0);
    for (std::size_t j = 0; j < controlCount; ++j) {
      int parameter;
      std::cin >> parameter;
      auto control = std::make_unique<Control>(static_cast<int>(j));
      if (parameter >= 0)
        control->setParameter(params.at(parameter), 0);
      group->add(control.get());
      controls.push_back(std::move(control));
    }
    roster.groups.add(group.get());
    groups.push_back(std::move(group));
  }
  if (!std::cin)
    throw std::runtime_error("incomplete fixture");
  ControlRegistrar registrar(roster);
  FixturePanel instance;
  instance.bindControlRegistrar(registrar);
  const Presonus::Panel::PanelComponent &panel = instance;
  const auto &parameter = *params.at(parameterIndex);
  const auto value = parameter.getValue();
  bool result = panel.isInGroup(query, parameter);
  if (parameter.getValue() != value ||
      registrar.count() != static_cast<int>(groupCount))
    throw std::runtime_error(
        "query mutated parameter value or registrar count");
  return result;
}
} // namespace

int main() {
  int query, parameter;
  std::size_t groupCount;
  if (!(std::cin >> query >> parameter >> groupCount))
    return 2;
  std::cout << runCase(query, parameter, groupCount) << '\n';
}
