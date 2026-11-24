#include "presonus/surface/CapturePageComponent.hpp"
#include <array>
#include <cstdio>
#include <cstring>

template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}

int main() {
  using namespace Presonus;
  for (unsigned index = 0; index < 3; ++index) {
    IDAWComponentObserver observer;

    const auto before = snapshot(observer);

    observer.onObjectChanged(
        static_cast<IDAWComponentObserver::ObjectChangeMessage>(
            index == 2 ? 0xffffffffu : index));
    if (!(before == snapshot(observer)))
      return 2;
    std::printf("%u 0 0\n", index);
  }
}
