#include "presonus/mixer/AVBCascadeManager.hpp"
#include "presonus/uc/NetworkItem.hpp"

#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>

namespace {
struct Boundary final : presonus::mixer::CascadeBoundary {
  void select(Presonus::UC::NetworkItem *, bool) override { std::abort(); }
  bool connectedClientPresent() override { std::abort(); }
  void connectionChanged(bool) override { std::abort(); }
  void updateChannelSelectionSync() override { std::abort(); }
};

template <class T> auto bytes(const T &value) {
  std::array<unsigned char, sizeof(T)> result;
  std::memcpy(result.data(), &value, sizeof(T));
  return result;
}
} // namespace

int main() {
  Boundary boundary;
  int selectedComponent = 17;
  int otherComponent = 42;
  Presonus::UC::NetworkItem selected(&selectedComponent);
  Presonus::UC::NetworkItem other(&otherComponent);
  Presonus::Mixer::AVBCascadeManager manager(boundary, &selected);
  for (auto *argument :
       std::array<Presonus::UC::NetworkItem *, 3>{nullptr, &selected, &other}) {
    const auto receiver = bytes(manager);
    const auto selectedBefore = bytes(selected);
    const auto otherBefore = bytes(other);
    manager.onServerChanged(argument);
    if (receiver != bytes(manager) || selectedBefore != bytes(selected) ||
        otherBefore != bytes(other) || selectedComponent != 17 ||
        otherComponent != 42)
      return 1;
    std::cout << (argument == nullptr     ? "null"
                  : argument == &selected ? "selected"
                                          : "other")
              << " 1 0\n";
  }
}
