#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/uc/ClientSubscription.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>

namespace {
using Presonus::Mixer::PermissionsBindings;
using Presonus::Mixer::PermissionsComponent;

void unusedBoundary(void *, PermissionsComponent &) { std::abort(); }

bool unchanged(int state) {
  Presonus::UC::ClientSubscription client(23);
  PermissionsBindings bindings;
  bindings.selectedSnapshot = state == 1 ? &client : nullptr;
  bindings.dirty = static_cast<unsigned char>(state);
  bindings.restricted = static_cast<unsigned char>(state * 11);
  bindings.deadlineMilliseconds = state * 101;
  if (state != 0) {
    bindings.loadSelectedDevice = unusedBoundary;
    bindings.devicePermissionsChanged = unusedBoundary;
  }

  PermissionsComponent component(bindings);
  if (state == 2) {
    component.portableOwnSelected(&client);
    component.portableAppendDevice(&client);
  }
  std::array<unsigned char, sizeof(component)> componentBefore;
  std::array<unsigned char, sizeof(bindings)> bindingsBefore;
  std::array<unsigned char, sizeof(client)> clientBefore;
  std::memcpy(componentBefore.data(), &component, componentBefore.size());
  std::memcpy(bindingsBefore.data(), &bindings, bindingsBefore.size());
  std::memcpy(clientBefore.data(), &client, clientBefore.size());
  const auto *const selected = component.getSelectedDevice();
  component.onPermissionsChanged();
  return std::memcmp(componentBefore.data(), &component,
                     componentBefore.size()) == 0 &&
         std::memcmp(bindingsBefore.data(), &bindings, bindingsBefore.size()) ==
             0 &&
         std::memcmp(clientBefore.data(), &client, clientBefore.size()) == 0 &&
         component.getSelectedDevice() == selected &&
         component.portableDeviceCount() == (state == 2 ? 1 : 0) &&
         (state != 2 || component.portableDeviceStorage()[0] == &client);
}
} // namespace

int main() {
  for (int state = 0; state < 3; ++state) {
    if (!unchanged(state))
      return 1;
    std::cout << state << " unchanged\n";
  }
}
