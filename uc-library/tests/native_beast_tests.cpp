#include "presonus/panel/BeastPanelRegistrar.hpp"

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>

int main(int argc, char **argv) {
  const Presonus::Panel::BeastPanelRegistrar registrar;
  if (argc == 3) {
    int count = static_cast<int>(std::strtoll(argv[2], nullptr, 10));
    const auto *tags = registrar.getTags(
        static_cast<int>(std::strtoll(argv[1], nullptr, 10)), count);
    std::cout << (tags ? 1 : 0) << ' ' << count;
    if (tags)
      for (int i = 0; i < count; ++i)
        std::cout << ' ' << static_cast<std::uint32_t>(tags[i]);
    std::cout << '\n';
    return 0;
  }
  constexpr int groups[] = {std::numeric_limits<int>::min(), -1, 0, 19, 20, 21,
                            std::numeric_limits<int>::max()};
  constexpr std::int32_t expected[] = {
      20, 21, 22, 23, -1, -1, -1, -1, 12, 13, 14, 15, 16, 17, 18, 19,
      8,  9,  10, 11, -1, -1, -1, -1, 0,  1,  2,  3,  4,  5,  6,  7};
  for (int group : groups) {
    int count = -12345;
    const auto *tags = registrar.getTags(group, count);
    if (group != 20) {
      if (tags != nullptr || count != -12345)
        return 1;
    } else {
      if (!tags || count != 32)
        return 2;
      for (int i = 0; i < count; ++i)
        if (tags[i] != expected[i])
          return 3;
      int nextCount = 0;
      if (registrar.getTags(20, nextCount) != tags || nextCount != 32)
        return 4;
    }
  }
  return 0;
}
