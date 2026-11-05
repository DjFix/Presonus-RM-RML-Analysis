#include "presonus/StormMixSceneComponent.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
struct Recall final : presonus::scene_port::Recall {
  bool recall(unsigned int) const override { return false; }
};
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int index = static_cast<int>(std::strtol(argv[1], nullptr, 10));
  const char *prefix = std::string(argv[2]) == "<null>" ? nullptr : argv[2];
  Recall recall;
  Presonus::StormMixSceneComponent object(recall);
  if (std::string(argv[2]) != "<original>")
    Presonus::StormMixSceneComponent::kDefaultName = prefix;
  auto result = object.createDefaultName(index);
  std::cout << result.str();
}
