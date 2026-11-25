#include "presonus/panel/registrar_group_registry.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"

#include <array>
#include <cassert>
#include <iostream>

int main() {
  using Presonus::Panel::ControlGroup;
  using Presonus::Panel::ControlRegistrar;
  using presonus::panel_binding::ControlGroupAccess;
  using presonus::panel_binding::RegistrarGroupRegistry;

  ControlGroup first(12, 0);
  ControlGroup second(3, 0);
  ControlGroup duplicate(12, 0);
  ControlGroup negative(-2, 0);
  ControlGroup zero(0, 0);
  const std::array<ControlGroup *, 5> groups = {&first, &second, &duplicate,
                                                &negative, &zero};
  RegistrarGroupRegistry empty, mixed;
  for (auto *group : groups)
    assert(mixed.groups.add(group));

  const ControlRegistrar registrars[] = {ControlRegistrar(empty),
                                         ControlRegistrar(mixed)};
  ControlGroup *sentinel = nullptr;
  int registrarIndex = 0;
  int tag = 0;
  while (std::cin >> registrarIndex >> tag) {
    const auto &registrar = registrars[registrarIndex];
    auto *result = registrar.findGroup(tag);
    assert(result);
    int found = -1;
    for (int index = 0; index < static_cast<int>(groups.size()); ++index) {
      if (result == groups[index])
        found = index;
    }
    if (found == -1) {
      if (!sentinel)
        sentinel = result;
      assert(sentinel == result);
    }
    std::cout << found << ' ' << ControlGroupAccess::groupId(*result) << ' '
              << result->count() << ' ' << (result->at(0) == nullptr) << ' '
              << (result->byTag(12) == nullptr) << ' ' << registrar.count();
    for (int index = 0; index < registrar.count(); ++index) {
      assert(registrar.at(index) == groups[index]);
      std::cout << ' ' << ControlGroupAccess::groupId(*registrar.at(index));
    }
    std::cout << '\n';
  }
}
