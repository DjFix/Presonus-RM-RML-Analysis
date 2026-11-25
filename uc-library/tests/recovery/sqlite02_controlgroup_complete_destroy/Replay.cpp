#include "presonus/panel/control.hpp"
#include "presonus/surface_panel/ControlGroup.hpp"

#include <array>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <string_view>

using Presonus::Panel::Control;
using Presonus::Panel::ControlGroup;
using presonus::panel_binding::ControlGroupAccess;
using presonus::panel_binding::ControlGroupState;

namespace {
std::array<void *, 4> tracked{};
std::array<int, 4> freed{};
std::size_t freeCount = 0;

void observeFree(void *pointer) {
  for (std::size_t index = 0; index < tracked.size(); ++index) {
    if (pointer && pointer == tracked[index]) {
      if (freeCount >= freed.size())
        std::abort();
      freed[freeCount++] = static_cast<int>(index);
      break;
    }
  }
}

struct DerivedGroup : ControlGroup {
  DerivedGroup() : ControlGroup(42, 0) {}
};
} // namespace

extern "C" void __real__ZdlPv(void *pointer) noexcept;
extern "C" void __real__ZdlPvm(void *pointer, std::size_t size) noexcept;

extern "C" void __wrap__ZdlPv(void *pointer) noexcept {
  observeFree(pointer);
  __real__ZdlPv(pointer);
}

extern "C" void __wrap__ZdlPvm(void *pointer, std::size_t size) noexcept {
  observeFree(pointer);
  __real__ZdlPvm(pointer, size);
}

int main(int argc, char **argv) {
  if (argc < 2)
    return 1;
  const std::string_view variant = argv[1];
  const auto populate = [&](ControlGroup &group) {
    tracked[0] = &group;
    for (int index = 2; index < argc; ++index) {
      const auto id = std::atoi(argv[index]);
      if (id < 0 || id > 2)
        std::abort();
      std::unique_ptr<Control> control;
      if (id != 0) {
        control = std::make_unique<Control>(id);
        tracked[id] = control.get();
      }
      if (!ControlGroupAccess::addOwned(group, std::move(control)) || control ||
          group.at(index - 2) != (id ? tracked[id] : nullptr))
        std::abort();
    }
  };

  if (variant == "D0") {
    ControlGroup *group = new ControlGroup(42, 0);
    populate(*group);
    delete group;
  } else if (variant == "D1") {
    ControlGroup group(42, 0);
    populate(group);
  } else if (variant == "D2") {
    DerivedGroup group;
    populate(group);
  } else {
    return 1;
  }

  std::cout << (freeCount && freed[freeCount - 1] == 0 ? "freed" : "retained");
  for (std::size_t index = 0; index < freeCount; ++index)
    std::cout << ' '
              << (freed[index] == 0 ? "group" : std::to_string(freed[index]));
  std::cout << '\n';

  tracked = {};
  freeCount = 0;
  {
    auto borrowed = std::make_unique<Control>(7);
    tracked[3] = borrowed.get();
    ControlGroupState injected;
    {
      ControlGroup group(42, 0);
      group.add(borrowed.get());
    }
    {
      ControlGroup group(injected);
      group.add(borrowed.get());
      if (ControlGroupAccess::addOwned(group, std::move(borrowed)) || !borrowed)
        return 2;
    }
    if (freeCount != 0 || injected.controls.count() != 1 ||
        injected.controls.at(0) != borrowed.get())
      return 2;
  }
  if (freeCount != 1 || freed[0] != 3)
    return 2;
  return 0;
}
