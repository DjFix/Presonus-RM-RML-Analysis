#include "presonus/uc/NetworkItem.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <new>
#include <string>
#include <string_view>
#include <type_traits>

using Presonus::UC::NetworkItem;

static_assert(!std::has_virtual_destructor_v<NetworkItem>);

namespace {
struct DerivedItem : NetworkItem {
  using NetworkItem::NetworkItem;
  unsigned marker = 0x7bc8;
  ~DerivedItem() = default;
};

template <typename Item> bool run(bool borrowed, std::string_view identity) {
  constexpr auto canary = std::byte{0x5a};
  constexpr std::size_t padding = alignof(Item);
  alignas(Item) std::array<std::byte, sizeof(Item) + 2 * padding> storage;
  storage.fill(canary);
  unsigned pointee = 0xaabbccdd;
  void *handle = borrowed ? &pointee : nullptr;
  auto *item = ::new (storage.data() + padding) Item(handle);
  const std::string text{identity};
  item->setPortableIdentity(text.c_str());
  const bool initialized =
      item->getComponent() == handle &&
      std::string_view{static_cast<const char *>(item->portableIdentity())} ==
          identity.substr(0, 63);
  // Calling the derived destructor runs the base-subobject destructor.
  const auto before = storage;
  item->~Item();
  return initialized && storage == before && pointee == 0xaabbccdd;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 4)
    return EXIT_FAILURE;
  const std::string_view variant{argv[1]};
  const std::string_view binding{argv[2]};
  if ((variant != "D1" && variant != "D2") ||
      (binding != "borrowed" && binding != "null"))
    return EXIT_FAILURE;
  const bool borrowed = binding == "borrowed";
  const bool preserved = variant == "D1" ? run<NetworkItem>(borrowed, argv[3])
                                         : run<DerivedItem>(borrowed, argv[3]);
  if (!preserved)
    return EXIT_FAILURE;
  std::cout << "returned storage-unchanged pointee-unchanged\n";
}
