#include "presonus/mixer/EarlyRefFormatterT5.hpp"

#include <array>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>

namespace {
const void *receiver = nullptr;
bool released = false;

template <class Type> bool exercise(float value) {
  Type parentProbe;
  const Core::Formatter *registered =
      Core::FormatterRegistry::find(parentProbe.getName());
  if (!registered)
    return false;

  std::array<char, 24> expected{};
  std::array<char, 24> actual{};
  Core::Formatter::Data baseData{nullptr, expected.data(), expected.size(),
                                 value, nullptr};
  Core::Formatter::Data taggedData{nullptr, actual.data(), actual.size(), value,
                                   nullptr};
  const Presonus::Mixer::EarlyRefFormatter parent;
  parent.print(baseData);
  registered->print(taggedData);
  if (actual != expected ||
      registered->scan(taggedData) != parent.scan(baseData))
    return false;

  Core::Formatter *heap = new Type;
  receiver = heap;
  released = false;
  delete heap;
  bool allocatedReceiverReleased = released;
  alignas(Type) std::array<std::byte, sizeof(Type)> placementStorage{};
  auto *placed = ::new (placementStorage.data()) Type;
  receiver = placed;
  released = false;
  placed->~Type();
  placementStorage.front() = std::byte{0x51};
  receiver = nullptr;
  std::cout << registered->getName() << '|' << allocatedReceiverReleased << '|'
            << released << '\n';
  return true;
}
} // namespace

void *operator new(std::size_t size) {
  if (void *storage = std::malloc(size ? size : 1))
    return storage;
  throw std::bad_alloc();
}

void operator delete(void *storage) noexcept {
  if (storage && storage == receiver)
    released = true;
  std::free(storage);
}

void operator delete(void *storage, std::size_t) noexcept {
  if (storage && storage == receiver)
    std::abort();
  std::free(storage);
}

int main() {
  Core::FormatterRegistry::add<Presonus::Mixer::EarlyRefFormatterT5>();
  float value;
  while (std::cin >> value)
    if (!exercise<Presonus::Mixer::EarlyRefFormatterT5>(value))
      return 1;
}
