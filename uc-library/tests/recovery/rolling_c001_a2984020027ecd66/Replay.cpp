#include "presonus/surface/CapturePageComponent.hpp"
#include <array>
#include <cstdio>
#include <cstring>

template <typename T> T *pointer(unsigned index, unsigned *storage) {
  return index ? reinterpret_cast<T *>(&storage[index - 1]) : nullptr;
}

template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}

int main() {
  using namespace Presonus;
  for (unsigned index = 0; index < 3; ++index) {
    IDAWComponentObserver observer;
    unsigned argument[] = {17, 33};
    unsigned second[] = {49, 65};
    const auto before = snapshot(observer);
    auto oldArgument = snapshot(argument);
    auto oldSecond = snapshot(second);
    observer.onChannelParamChanged(
        pointer<DAWChannel>(index, argument),
        pointer<Core::Portable::Parameter>(2 - index, second));
    if (!(before == snapshot(observer) && oldArgument == snapshot(argument) &&
          oldSecond == snapshot(second)))
      return 2;
    std::printf("%u 0 0\n", index);
  }
}
