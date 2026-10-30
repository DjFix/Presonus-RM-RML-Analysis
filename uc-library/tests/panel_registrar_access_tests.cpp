#include "presonus/panel/registrar_group_registry.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <array>
#include <cassert>
#include <fstream>
#include <iostream>
#include <memory>
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  using Group = Presonus::Panel::ControlGroup;
  std::array<presonus::panel_binding::ControlGroupState, 17> storage;
  std::array<std::unique_ptr<Group>, 17> groups;
  for (unsigned i = 0; i < groups.size(); ++i)
    groups[i] = std::make_unique<Group>(storage[i]);
  auto pointer = [&](int value) -> Group * {
    assert(value >= -1 && value < static_cast<int>(groups.size()));
    return value < 0 ? nullptr : groups[static_cast<unsigned>(value)].get();
  };
  presonus::panel_binding::RegistrarGroupRegistry registry;
  const Presonus::Panel::ControlRegistrar registrar(registry);
  auto &sharedError = Core::ConstVector<Group *>::getError();
  auto *savedError = sharedError;
  int count, index, error, expected;
  unsigned cases = 0;
  while (input >> count >> index >> error >> expected) {
    assert(count >= 0 && count <= 16);
    registry.groups.removeAll();
    for (int i = 0; i < count; ++i) {
      int value;
      assert(input >> value);
      assert(registry.groups.add(pointer(value)));
    }
    sharedError = pointer(error);
    assert(registrar.count() == count);
    assert(registrar.at(index) == pointer(expected));
    assert(registry.groups.count() == count);
    assert(sharedError == pointer(error));
    ++cases;
  }
  sharedError = savedError;
  assert(input.eof() && cases == 2048);
  std::cout << "PASS2048 count_at_real_CCL_vector_and_shared_error\n";
}
