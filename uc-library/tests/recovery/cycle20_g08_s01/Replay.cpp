#include "presonus/ModalPageComponent.hpp"

#include <array>
#include <iostream>
#include <type_traits>

using Presonus::ModalPageComponent;

int main() {
  static_assert(std::is_same_v<decltype(&ModalPageComponent::onOk),
                               bool (ModalPageComponent::*)()>);
  struct Fixture {
    unsigned before;
    ModalPageComponent page;
    unsigned after;
  };
  constexpr std::array<int, 5> classIds{1299145808, 1348560741, 1131375984, 0,
                                        -1};
  unsigned seed, unusedR2;
  while (std::cin >> seed >> unusedR2) {
    const unsigned trailing = seed ^ unusedR2;
    Fixture fixture{seed, {}, trailing};
    std::array<void *, classIds.size()> original{};
    for (std::size_t index = 0; index < classIds.size(); ++index)
      original[index] = fixture.page.castTo(classIds[index]);

    const bool result = fixture.page.onOk();
    for (std::size_t index = 0; index < classIds.size(); ++index) {
      void *expected = index < 3 ? &fixture.page : nullptr;
      if (original[index] != expected ||
          fixture.page.castTo(classIds[index]) != original[index])
        return 2;
    }
    if (fixture.before != seed || fixture.after != trailing)
      return 3;
    std::cout << result << '\n';
  }
  return std::cin.eof() ? 0 : 4;
}
