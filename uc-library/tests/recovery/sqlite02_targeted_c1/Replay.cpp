#include "presonus/TargetedComponent.hpp"
#include <cstring>
#include <iostream>

namespace {
class Derived final : public Presonus::TargetedComponent {
public:
  explicit Derived(const char *name) : TargetedComponent(name) {}
  void doUpdates() override {
    phase = phase == 0 && portablePendingUpdates() == 0 ? 1 : -1;
  }
  void postDoUpdates() override { phase = phase == 1 ? 2 : -1; }
  int phase = 0;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  Presonus::TargetedComponent component(argv[1]);
  Presonus::TargetedComponent tagged(
      Presonus::TargetedComponent::SourcePortConstruction{});
  auto &server = static_cast<Presonus::UC::ServerComponent &>(component);
  std::cout << (std::strcmp(server.getName(), argv[1]) == 0) << ' '
            << static_cast<int>(component.portablePendingUpdates()) << ' '
            << (0) << ' ';
  component.onIdle();
  std::cout << (0) << ' ';
  component.portableMarkUpdatesPending(0xa5);
  component.onIdle();
  std::cout << (0) << ' '
            << static_cast<int>(component.portablePendingUpdates()) << ' ';
  component.onIdle();
  std::cout << (0) << ' ' << (tagged.getName()[0] == '\0') << ' '
            << static_cast<int>(tagged.portablePendingUpdates()) << '\n';
}
